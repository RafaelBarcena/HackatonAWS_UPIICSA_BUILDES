"""Configuración de RutaAlerta. Cada valor se puede sobrescribir con una variable de entorno."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

REGION = os.environ.get("AWS_REGION", "us-west-2")
BUCKET = os.environ.get("RUTAALERTA_BUCKET", "rutaalerta-demo-datos")
KEY_RUTAS = os.environ.get("RUTAALERTA_KEY_RUTAS", "rutas.json")
KEY_INCIDENTES = os.environ.get("RUTAALERTA_KEY_INCIDENTES", "incidentes.json")
TOPIC_NAME = os.environ.get("RUTAALERTA_TOPIC_NAME", "rutaalerta-alertas")
TOPIC_ARN = os.environ.get("RUTAALERTA_TOPIC_ARN", "")
EMAIL = os.environ.get("RUTAALERTA_EMAIL", "cambia-esto@ejemplo.com")
SMS = os.environ.get("RUTAALERTA_SMS", "")
RUTA_ID = os.environ.get("RUTAALERTA_RUTA_ID", "casa-trabajo")


def _entero(nombre, defecto):
    try:
        valor = int(os.environ.get(nombre, defecto))
        return valor if valor > 0 else defecto
    except ValueError:
        return defecto


INTERVALO = _entero("RUTAALERTA_INTERVALO", 180)
