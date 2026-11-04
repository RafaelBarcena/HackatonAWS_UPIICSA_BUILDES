"""Lógica pura de RutaAlerta: parseo, evaluación de la ruta y formato de mensajes."""
import re
import unicodedata

TIPOS = {
    "transporte_retrasado": "Transporte retrasado",
    "estacion_cerrada": "Estación cerrada",
    "calle_bloqueada": "Calle bloqueada",
    "manifestacion": "Manifestación",
    "evento": "Evento",
}
ORDEN_SEVERIDAD = {"baja": 1, "media": 2, "alta": 3}
AVISOS = {"1dia": "1 día antes", "10min": "10 minutos antes"}


def normalizar(texto):
    """Compara tramos sin distinguir mayúsculas, acentos ni espacios extra."""
    t = unicodedata.normalize("NFKD", str(texto).strip())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.casefold().split())


# ---------------------------------------------------------------- parseo

def parsear_rutas(datos):
    rutas = datos.get("rutas", []) if isinstance(datos, dict) else []
    return [r for r in rutas if r.get("id") and isinstance(r.get("tramos"), list)]


def parsear_incidentes(datos):
    incs = datos.get("incidentes", []) if isinstance(datos, dict) else []
    return [i for i in incs if isinstance(i, dict) and i.get("id")]


def parsear_tramos(texto):
    """'Metro A, Linea 3 -> Calle X' -> ['Metro A', 'Linea 3', 'Calle X']."""
    texto = str(texto).replace("->", ",").replace("→", ",")
    return [p.strip() for p in re.split(r"[,;\n]+", texto) if p.strip()]


def ruta_personalizada(texto, nombre=None):
    tramos = parsear_tramos(texto)
    if not tramos:
        raise ValueError("Escribe al menos un tramo (separados por comas).")
    return {
        "id": "personalizada",
        "nombre": nombre or "Ruta personalizada",
        "origen": tramos[0],
        "destino": tramos[-1],
        "hora_salida_habitual": "",
        "tramos": tramos,
    }


def buscar_ruta(rutas, ruta_id):
    for r in rutas:
        if r["id"] == ruta_id:
            return r
    disponibles = ", ".join(r["id"] for r in rutas) or "ninguna"
    raise KeyError("Ruta '%s' no encontrada. Disponibles: %s" % (ruta_id, disponibles))


# ------------------------------------------------------------ evaluación

def _sev(inc):
    return ORDEN_SEVERIDAD.get(inc.get("severidad"), 1)


def evaluar_ruta(ruta, incidentes):
    """Cruza los tramos de la ruta con los incidentes vigentes."""
    tramos, afectados, vistos = [], [], set()
    for nombre in ruta["tramos"]:
        clave = normalizar(nombre)
        incs = [i for i in incidentes
                if i.get("vigente") is True and normalizar(i.get("tramo", "")) == clave]
        estado = "ok"
        if incs:
            estado = max(incs, key=_sev).get("severidad", "baja")
            if estado not in ORDEN_SEVERIDAD:
                estado = "baja"
        tramos.append({"nombre": nombre, "estado": estado, "incidentes": incs})
        for i in incs:
            if i["id"] not in vistos:
                vistos.add(i["id"])
                afectados.append(i)
    severidad_max = max((_sev(i) for i in afectados), default=0)
    inverso = {v: k for k, v in ORDEN_SEVERIDAD.items()}
    return {
        "ruta": ruta,
        "tramos": tramos,
        "incidentes": afectados,
        "total": len(afectados),
        "estado": "incidencias" if afectados else "despejada",
        "severidad_max": inverso.get(severidad_max, "ok"),
        "firma": tuple(sorted(vistos)),
    }


# --------------------------------------------------------------- mensajes

def _linea(inc):
    tipo = TIPOS.get(inc.get("tipo"), inc.get("tipo", "Incidente"))
    return "- [%s] %s en %s: %s" % (
        str(inc.get("severidad", "?")).upper(), tipo, inc.get("tramo", "?"),
        inc.get("descripcion", ""))


def formatear_alerta(ev):
    r = ev["ruta"]
    asunto = "RutaAlerta: %d incidencia(s) en %s" % (ev["total"], r["nombre"])
    cuerpo = "Hay %d incidencia(s) en tu ruta %s:\n%s" % (
        ev["total"], r["nombre"], "\n".join(_linea(i) for i in ev["incidentes"]))
    return asunto, cuerpo


def formatear_despejada(ev):
    r = ev["ruta"]
    return ("RutaAlerta: ruta despejada (%s)" % r["nombre"],
            "Tu ruta %s ya no tiene incidencias vigentes. Buen viaje." % r["nombre"])


def formatear_aviso(ev, tipo):
    if tipo not in AVISOS:
        raise ValueError("Tipo de aviso inválido: %s (usa 1dia o 10min)" % tipo)
    r = ev["ruta"]
    salida = r.get("hora_salida_habitual")
    cuando = " (salida habitual %s)" % salida if salida else ""
    asunto = "RutaAlerta: aviso %s - %s" % (AVISOS[tipo], r["nombre"])
    cabecera = "Aviso %s de tu ruta %s%s." % (AVISOS[tipo], r["nombre"], cuando)
    if ev["total"]:
        detalle = "Estado actual: %d incidencia(s):\n%s" % (
            ev["total"], "\n".join(_linea(i) for i in ev["incidentes"]))
    else:
        detalle = "Estado actual: ruta despejada, sin incidencias."
    return asunto, cabecera + "\n" + detalle


# -------------------------------------------------------------- vigilante

class Vigilante:
    """Notifica solo cuando cambia el estado de la ruta (evita spam)."""

    def __init__(self, notificar):
        self.notificar = notificar  # callable(asunto, cuerpo)
        self.ultimas = {}

    def ciclo(self, ruta, incidentes):
        ev = evaluar_ruta(ruta, incidentes)
        clave = (ruta["id"], tuple(normalizar(t) for t in ruta["tramos"]))
        previa = self.ultimas.get(clave)
        notificado = False
        if ev["firma"] != (previa if previa is not None else ()):
            if ev["total"]:
                self.notificar(*formatear_alerta(ev))
            else:
                self.notificar(*formatear_despejada(ev))
            notificado = True
        self.ultimas[clave] = ev["firma"]
        return ev, notificado
