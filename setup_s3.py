"""Crea el bucket S3 (si no existe) y sube rutas.json e incidentes.json."""
import sys

import boto3
from botocore.exceptions import ClientError

import config


def main():
    s3 = boto3.client("s3", region_name=config.REGION)
    args = {"Bucket": config.BUCKET}
    if config.REGION != "us-east-1":
        args["CreateBucketConfiguration"] = {"LocationConstraint": config.REGION}
    try:
        s3.create_bucket(**args)
        print("Bucket creado: %s" % config.BUCKET)
    except ClientError as e:
        codigo = e.response["Error"]["Code"]
        if codigo == "BucketAlreadyOwnedByYou":
            print("El bucket ya existe y es tuyo: %s" % config.BUCKET)
        elif codigo == "BucketAlreadyExists":
            print("El nombre '%s' ya lo usa otra cuenta. Cambia RUTAALERTA_BUCKET." % config.BUCKET)
            return 1
        else:
            raise
    for key, archivo in ((config.KEY_RUTAS, "rutas.json"), (config.KEY_INCIDENTES, "incidentes.json")):
        s3.upload_file(str(config.DATA_DIR / archivo), config.BUCKET, key,
                       ExtraArgs={"ContentType": "application/json"})
        print("Subido: s3://%s/%s" % (config.BUCKET, key))
    return 0


if __name__ == "__main__":
    sys.exit(main())
