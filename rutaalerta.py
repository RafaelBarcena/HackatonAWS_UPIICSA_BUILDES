"""RutaAlerta: avisos de incidentes en tu ruta habitual (consola y GUI web local)."""
import argparse
import sys
import time
from datetime import datetime

import config
from core import (Vigilante, buscar_ruta, evaluar_ruta, formatear_alerta,
                  formatear_aviso, ruta_personalizada)
from datasource import cargar_datos
from notifier import Notificador


def resolver_ruta(rutas, args):
    if getattr(args, "tramos", None):
        return ruta_personalizada(args.tramos)
    return buscar_ruta(rutas, args.ruta)


def cmd_check(args, notificador):
    rutas, incs, origen = cargar_datos(args.local)
    ev = evaluar_ruta(resolver_ruta(rutas, args), incs)
    print("Datos: %s | Ruta: %s" % (origen, ev["ruta"]["nombre"]))
    if ev["total"]:
        notificador.enviar(*formatear_alerta(ev))
    else:
        print("Ruta despejada: sin incidencias vigentes.")


def cmd_aviso(args, notificador):
    rutas, incs, origen = cargar_datos(args.local)
    ev = evaluar_ruta(resolver_ruta(rutas, args), incs)
    notificador.enviar(*formatear_aviso(ev, args.tipo))


def cmd_monitor(args, notificador):
    vigilante = Vigilante(notificador.enviar)
    print("Monitoreando cada %d s. Ctrl+C para detener." % args.intervalo)
    try:
        while True:
            rutas, incs, origen = cargar_datos(args.local)
            ev, notificado = vigilante.ciclo(resolver_ruta(rutas, args), incs)
            print("[%s] datos=%s | %s | %d incidencia(s)%s" % (
                datetime.now().strftime("%H:%M:%S"), origen, ev["estado"], ev["total"],
                " | notificado" if notificado else ""))
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nMonitoreo detenido.")


def cmd_gui(args, notificador):
    import gui
    gui.servir(args, notificador)


def crear_parser():
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--ruta", default=config.RUTA_ID, help="ID de ruta (rutas.json)")
    comun.add_argument("--tramos", help="Ruta propia: tramos separados por comas")
    comun.add_argument("--local", action="store_true", help="Leer JSON de data/ en vez de S3")
    comun.add_argument("--no-sns", action="store_true", help="No publicar en SNS")

    p = argparse.ArgumentParser(prog="rutaalerta", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", parents=[comun], help="Evalúa la ruta una vez")
    a = sub.add_parser("aviso", parents=[comun], help="Dispara un aviso manual")
    a.add_argument("--tipo", choices=["1dia", "10min"], required=True)
    m = sub.add_parser("monitor", parents=[comun], help="Bucle de monitoreo")
    m.add_argument("--intervalo", type=int, default=config.INTERVALO, help="Segundos entre ciclos")
    g = sub.add_parser("gui", parents=[comun], help="Interfaz web local")
    g.add_argument("--puerto", type=int, default=8080)
    g.add_argument("--intervalo", type=int, default=config.INTERVALO)
    g.add_argument("--no-abrir", action="store_true", help="No abrir el navegador")
    return p


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = crear_parser().parse_args(argv)
    if getattr(args, "intervalo", 1) < 1:
        print("--intervalo debe ser mayor que 0.")
        return 2
    notificador = Notificador(usar_sns=not args.no_sns)
    try:
        {"check": cmd_check, "aviso": cmd_aviso,
         "monitor": cmd_monitor, "gui": cmd_gui}[args.cmd](args, notificador)
    except (KeyError, ValueError) as e:
        print("Error: %s" % (e.args[0] if e.args else e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
