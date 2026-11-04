"""Crea el topic SNS y suscribe el correo configurado."""
import boto3

import config


def main():
    sns = boto3.client("sns", region_name=config.REGION)
    arn = sns.create_topic(Name=config.TOPIC_NAME)["TopicArn"]
    print("TopicArn: %s" % arn)
    sns.subscribe(TopicArn=arn, Protocol="email", Endpoint=config.EMAIL)
    print("Suscripción enviada a %s. Confirma el correo de AWS." % config.EMAIL)
    if config.SMS:
        print("SMS: se envía directo a %s (en sandbox debe estar verificado en SNS)." % config.SMS)
    print('\nPowerShell:\n$env:RUTAALERTA_TOPIC_ARN = "%s"' % arn)


if __name__ == "__main__":
    main()
