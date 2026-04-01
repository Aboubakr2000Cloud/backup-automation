#!/usr/bin/env python3

# config.py
import os
from pathlib import Path
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import logging

load_dotenv()

# Backup settings
RAW_BACKUP_SOURCES = os.getenv('BACKUP_SOURCES')
RAW_BACKUP_DESTINATION = os.getenv('BACKUP_DESTINATION')
RAW_RETENTION_DAYS = os.getenv('RETENTION_DAYS')
RAW_MIN_BACKUPS = os.getenv('MIN_BACKUPS_TO_KEEP')
RAW_S3_BACKUP_BUCKET = os.getenv('S3_BACKUP_BUCKET')
RAW_S3_PREFIX = os.getenv('S3_PREFIX')
RAW_UPLOAD_TO_S3 = os.getenv('UPLOAD_TO_S3')
RAW_DELETE_LOCAL_AFTER_UPLOAD = os.getenv('DELETE_LOCAL_AFTER_UPLOAD')
RAW_S3_RETENTION_DAYS = os.getenv('S3_RETENTION_DAYS', 30)


# Logging
LOG_FILE = 'logs/backup.log'
RAW_LOG_LEVEL = os.getenv('LOG_LEVEL')

# Validation functions
def validate_required_vars():
    required = {
        "BACKUP_SOURCES": RAW_BACKUP_SOURCES,
        "BACKUP_DESTINATION": RAW_BACKUP_DESTINATION,
        "RETENTION_DAYS": RAW_RETENTION_DAYS,
        "MIN_BACKUPS_TO_KEEP": RAW_MIN_BACKUPS,
        "LOG_LEVEL": RAW_LOG_LEVEL,
        "S3_RETENTION_DAYS": RAW_S3_RETENTION_DAYS,
        }

    missing = [k for k, v in required.items() if not v]

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

BACKUP_SOURCES = [Path(p.strip()).expanduser().resolve() for p in RAW_BACKUP_SOURCES.split(",")] if RAW_BACKUP_SOURCES else []
BACKUP_DESTINATION = Path(RAW_BACKUP_DESTINATION)
RETENTION_DAYS = int(RAW_RETENTION_DAYS)
MIN_BACKUPS = int(RAW_MIN_BACKUPS)
LOG_LEVEL = RAW_LOG_LEVEL
S3_BACKUP_BUCKET = RAW_S3_BACKUP_BUCKET
S3_PREFIX = S3_PREFIX = RAW_S3_PREFIX.rstrip("/") + "/" if RAW_S3_PREFIX else None
UPLOAD_TO_S3 = str(RAW_UPLOAD_TO_S3).lower() == "true"
DELETE_LOCAL_AFTER_UPLOAD = str(RAW_DELETE_LOCAL_AFTER_UPLOAD).lower() == "true"
S3_RETENTION_DAYS = int(RAW_S3_RETENTION_DAYS)

def validate_paths():
    for src in BACKUP_SOURCES:
        if not src.is_dir():
            raise ValueError(f"Backup source does not exist: {src}")
        if not os.access(src, os.R_OK):
            raise PermissionError(f"Backup source not readable: {src}")

    BACKUP_DESTINATION.mkdir(parents=True, exist_ok=True)

    if not os.access(BACKUP_DESTINATION, os.W_OK):
        raise PermissionError(
            f"Backup destination not writable: {BACKUP_DESTINATION}"
        )

def validate_s3_config():
    required = { 
        "S3_BACKUP_BUCKET": RAW_S3_BACKUP_BUCKET,
        "S3_PREFIX": RAW_S3_PREFIX,
        }

    missing = [k for k, v in required.items() if not v]

    if missing:
        raise RuntimeError(
            f"Missing required s3 environment variables: {', '.join(missing)}"
        )

def validate_bucket(s3, bucket, logger):
    try:
        s3.head_bucket(Bucket=bucket)
        logger.info(f"Bucket '{bucket}' is accessible")
        return True

    except ClientError as e:
        code = e.response["Error"]["Code"]

        if code == "404":
            logger.error(f"Bucket '{bucket}' does not exist")
        elif code == "403":
            logger.error(f"Access denied to bucket '{bucket}'")
        else:
            logger.error(f"Error accessing bucket: {code}")

        return False
