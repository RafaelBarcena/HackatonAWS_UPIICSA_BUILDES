"""Pruebas unitarias (no necesitan AWS). Ejecutar: python test_rutaalerta.py"""
import json
import unittest

import config
from core import (Vigilante, buscar_ruta, evaluar_ruta, formatear_alerta, formatear_aviso,
                  normalizar, parsear_incidentes, parsear_rutas, parsear_tramos,
                  ruta_personalizada)


def inc(id_, tramo, vigente=True, sev="alta"):
    return {"id": id_, "tipo": "estacion_cerrada", "tramo": tramo, "severidad": sev,
            "descripcion": "x", "vigente": vigente}


RUTA = {"id": "r", "nombre": "R", "tramos": ["Metro A", "Linea 3", "Metro B"],
        "hora_salida_habitual": "07:30"}


def datos_locales():
    with open(config.DATA_DIR / "rutas.json", encoding="utf-8") as f:
        rutas = parsear_rutas(json.load(f))
    with open(config.DATA_DIR / "incidentes.json", encoding="utf-8") as f:
        incs = parsear_incidentes(json.load(f))
    return rutas, incs


class Pruebas(unittest.TestCase):
    def test_01_normalizar_mayusculas_y_espacios(self):
        self.assertEqual(normalizar("  METRO   Chabacano "), normalizar("metro chabacano"))

    def test_02_normalizar_acentos(self):
        self.assertEqual(normalizar("Línea 9"), normalizar("linea 9"))

    def test_03_incidente_vigente_afecta(self):
        ev = evaluar_ruta(RUTA, [inc("1", " metro a ")])
        self.assertEqual(ev["total"], 1)
        self.assertEqual(ev["tramos"][0]["estado"], "alta")

    def test_04_incidente_no_vigente_no_afecta(self):
        self.assertEqual(evaluar_ruta(RUTA, [inc("1", "Metro A", vigente=False)])["total"], 0)

    def test_05_tramo_distinto_no_afecta(self):
        self.assertEqual(evaluar_ruta(RUTA, [inc("1", "Otra calle")])["estado"], "despejada")

    def test_06_datos_locales_casa_trabajo_tiene_2(self):
        rutas, incs = datos_locales()
        ev = evaluar_ruta(buscar_ruta(rutas, "casa-trabajo"), incs)
        self.assertEqual(sorted(i["tramo"] for i in ev["incidentes"]),
                         ["Linea 9", "Metro Chabacano"])

    def test_07_ruta_inexistente(self):
        with self.assertRaises(KeyError):
            buscar_ruta([RUTA], "nope")

    def test_08_tramos_personalizados(self):
        self.assertEqual(parsear_tramos("A, B -> C;\n D"), ["A", "B", "C", "D"])
        with self.assertRaises(ValueError):
            ruta_personalizada(" , ")
        self.assertEqual(ruta_personalizada("A,B")["destino"], "B")

    def test_09_alerta_menciona_tramo(self):
        asunto, cuerpo = formatear_alerta(evaluar_ruta(RUTA, [inc("1", "Metro B")]))
        self.assertIn("1 incidencia", asunto)
        self.assertIn("Metro B", cuerpo)

    def test_10_avisos(self):
        ev = evaluar_ruta(RUTA, [])
        self.assertIn("1 día antes", formatear_aviso(ev, "1dia")[0])
        self.assertIn("10 minutos antes", formatear_aviso(ev, "10min")[0])
        with self.assertRaises(ValueError):
            formatear_aviso(ev, "otro")

    def test_11_vigilante_solo_notifica_en_cambio(self):
        enviados = []
        v = Vigilante(lambda a, c: enviados.append(a))
        incs = [inc("1", "Metro A")]
        v.ciclo(RUTA, incs)
        v.ciclo(RUTA, incs)
        self.assertEqual(len(enviados), 1)
        v.ciclo(RUTA, incs + [inc("2", "Metro B")])
        self.assertEqual(len(enviados), 2)

    def test_12_vigilante_avisa_ruta_despejada(self):
        enviados = []
        v = Vigilante(lambda a, c: enviados.append(a))
        v.ciclo(RUTA, [inc("1", "Metro A")])
        v.ciclo(RUTA, [inc("1", "Metro A", vigente=False)])
        v.ciclo(RUTA, [inc("1", "Metro A", vigente=False)])
        self.assertEqual(len(enviados), 2)
        self.assertIn("despejada", enviados[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
