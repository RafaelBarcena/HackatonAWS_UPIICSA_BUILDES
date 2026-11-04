"""Notificaciones: consola siempre, correo vía topic SNS y SMS directo (opcionales)."""
import threading
from datetime import datetime

import config


class Notificador:
    def __init__(self, usar_sns=True):
        self.usar_sns = usar_sns
        self.historial = []
        self._sns = None
        self._lock = threading.Lock()

    def _cliente(self):
        if self._sns is None:
            import boto3
            self._sns = boto3.client("sns", region_name=config.REGION)
        return self._sns

    def _registrar(self, asunto, canal, ok, detalle=""):
        reg = {"asunto": asunto, "hora": datetime.now().strftime("%H:%M:%S"),
               "ts": datetime.now().isoformat(), "canal": canal, "ok": ok,
               "detalle": detalle}
        with self._lock:
            self.historial.append(reg)
            del self.historial[:-100]
        return reg

    def enviar(self, asunto, cuerpo):
        """Envía por todos los canales disponibles y devuelve los registros."""
        registros = []
        print("\n=== ALERTA %s ===\n%s\n%s\n" % (
            datetime.now().strftime("%H:%M:%S"), asunto, cuerpo))
        registros.append(self._registrar(asunto, "consola", True))
        if not self.usar_sns:
            return registros

        if config.TOPIC_ARN:
            try:
                self._cliente().publish(
                    TopicArn=config.TOPIC_ARN, Subject=asunto.replace("\n", " ")[:100],
                    Message=cuerpo)
                registros.append(self._registrar(asunto, "correo", True))
            except Exception as e:
                print("Correo (SNS) falló: %s" % e)
                registros.append(self._registrar(asunto, "correo", False, type(e).__name__))
        else:
            print("RUTAALERTA_TOPIC_ARN vacío: no se envía correo.")
            registros.append(self._registrar(asunto, "correo", False, "sin TOPIC_ARN"))

        if config.SMS:
            try:
                texto = (asunto + "\n" + cuerpo)[:300]
                self._cliente().publish(
                    PhoneNumber=config.SMS, Message=texto,
                    MessageAttributes={"AWS.SNS.SMS.SMSType": {
                        "DataType": "String", "StringValue": "Transactional"}})
                registros.append(self._registrar(asunto, "sms", True))
            except Exception as e:
                print("SMS falló: %s" % e)
                registros.append(self._registrar(asunto, "sms", False, type(e).__name__))
        return registros
