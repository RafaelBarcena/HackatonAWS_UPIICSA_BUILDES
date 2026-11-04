"""Servidor web local (http.server) para la interfaz gráfica de RutaAlerta."""
import json
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import config
from core import (TIPOS, Vigilante, buscar_ruta, evaluar_ruta, formatear_aviso,
                  ruta_personalizada)
from datasource import cargar_datos

HTML = config.BASE_DIR / "gui.html"


def _serializar(ev, origen, notificador, intervalo):
    return {
        "estado": ev["estado"],
        "total": ev["total"],
        "severidad_max": ev["severidad_max"],
        "ruta": {k: ev["ruta"].get(k, "") for k in ("id", "nombre", "origen", "destino",
                                                    "hora_salida_habitual")},
        "tramos": [{"nombre": t["nombre"], "estado": t["estado"],
                    "incidentes": [dict(i, etiqueta=TIPOS.get(i.get("tipo"), i.get("tipo", "Incidente")))
                                   for i in t["incidentes"]]}
                   for t in ev["tramos"]],
        "incidentes": [dict(i, etiqueta=TIPOS.get(i.get("tipo"), i.get("tipo", "Incidente")))
                       for i in ev["incidentes"]],
        "origen": origen,
        "hora": datetime.now().strftime("%H:%M:%S"),
        "intervalo": intervalo,
        "historial": list(reversed(notificador.historial[-30:])),
    }


def servir(args, notificador):
    vigilante = Vigilante(notificador.enviar)
    lock = threading.Lock()

    def resolver(rutas, ruta_id, tramos, nombre=None):
        if tramos and tramos.strip():
            return ruta_personalizada(tramos, (nombre or "").strip() or None)
        return buscar_ruta(rutas, ruta_id or config.RUTA_ID)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, codigo, obj):
            cuerpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            url = urlparse(self.path)
            q = parse_qs(url.query)
            try:
                if url.path in ("/", "/index.html"):
                    cuerpo = HTML.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(cuerpo)))
                    self.end_headers()
                    self.wfile.write(cuerpo)
                elif url.path == "/api/rutas":
                    with lock:
                        rutas, _, origen = cargar_datos(args.local)
                    self._json(200, {"rutas": rutas, "origen": origen,
                                     "intervalo": args.intervalo, "ruta_defecto": args.ruta,
                                     "tramos_defecto": args.tramos or ""})
                elif url.path == "/api/estado":
                    with lock:
                        rutas, incs, origen = cargar_datos(args.local)
                        ruta = resolver(rutas, q.get("ruta", [""])[0], q.get("tramos", [""])[0],
                                        q.get("nombre", [""])[0])
                        ev, _ = vigilante.ciclo(ruta, incs)
                    self._json(200, _serializar(ev, origen, notificador, args.intervalo))
                else:
                    self._json(404, {"error": "No encontrado"})
            except (KeyError, ValueError) as e:
                self._json(400, {"error": str(e.args[0] if e.args else e)})
            except Exception as e:
                self._json(500, {"error": "%s: %s" % (type(e).__name__, e)})

        def do_POST(self):
            if urlparse(self.path).path != "/api/aviso":
                return self._json(404, {"error": "No encontrado"})
            try:
                largo = int(self.headers.get("Content-Length", 0))
                datos = json.loads(self.rfile.read(largo) or b"{}")
                with lock:
                    rutas, incs, origen = cargar_datos(args.local)
                    ruta = resolver(rutas, datos.get("ruta"), datos.get("tramos"),
                                    datos.get("nombre"))
                    ev = evaluar_ruta(ruta, incs)
                    notificador.enviar(*formatear_aviso(ev, datos.get("tipo")))
                self._json(200, _serializar(ev, origen, notificador, args.intervalo))
            except (KeyError, ValueError) as e:
                self._json(400, {"error": str(e.args[0] if e.args else e)})
            except Exception as e:
                self._json(500, {"error": "%s: %s" % (type(e).__name__, e)})

    servidor = ThreadingHTTPServer(("127.0.0.1", args.puerto), Handler)
    url = "http://127.0.0.1:%d/" % args.puerto
    print("RutaAlerta GUI en %s (Ctrl+C para detener)" % url)
    if not args.no_abrir:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()
