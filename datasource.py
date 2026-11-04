"""Lectura de rutas e incidentes desde S3 con fallback a los JSON locales."""
import json
import sys

import config
from core import parsear_incidentes, parsear_rutas


def _leer_local(nombre):
    with open(config.DATA_DIR / nombre, encoding="utf-8") as f:
        return json.load(f)


def _leer_s3():
    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3", region_name=config.REGION,
        config=Config(connect_timeout=3, read_timeout=5, retries={"max_attempts": 1}))

    def get(key):
        obj = s3.get_object(Bucket=config.BUCKET, Key=key)
        return json.loads(obj["Body"].read().decode("utf-8"))

    return get(config.KEY_RUTAS), get(config.KEY_INCIDENTES)


def cargar_datos(local=False):
    """Devuelve (rutas, incidentes, origen) donde origen es 'S3' o 'local'."""
    if not local:
        try:
            rutas, incs = _leer_s3()
            return parsear_rutas(rutas), parsear_incidentes(incs), "S3"
        except Exception as e:  # sin credenciales, sin red, bucket inexistente...
            print("S3 no disponible (%s). Usando datos locales." % type(e).__name__,
                  file=sys.stderr)
    rutas = _leer_local("rutas.json")
    incs = _leer_local("incidentes.json")
    return parsear_rutas(rutas), parsear_incidentes(incs), "local"
