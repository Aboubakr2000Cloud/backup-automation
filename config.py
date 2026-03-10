#!/usr/bin/env python3

# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Backup settings
RAW_BACKUP_SOURCES = os.getenv('BACKUP_SOURCES')
RAW_BACKUP_DESTINATION = os.getenv('BACKUP_DESTINATION')
RAW_RETENTION_DAYS = os.getenv('RETENTION_DAYS')
RAW_MIN_BACKUPS = os.getenv('MIN_BACKUPS_TO_KEEP')

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
        }

    missing = [k for k, v in required.items() if not v]

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

BACKUP_SOURCES = [Path(p.strip()).expanduser().resolve() for p in RAW_BACKUP_SOURCES.split(",")]
BACKUP_DESTINATION = Path(RAW_BACKUP_DESTINATION)
RETENTION_DAYS = int(RAW_RETENTION_DAYS)
MIN_BACKUPS = int(RAW_MIN_BACKUPS)
LOG_LEVEL = RAW_LOG_LEVEL

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
