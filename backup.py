#!/usr/bin/env python3
import subprocess
import logging
import datetime
import hashlib
import json
import time
import argparse
from pathlib import Path
from config import BACKUP_SOURCES, BACKUP_DESTINATION, RETENTION_DAYS, MIN_BACKUPS, LOG_FILE, LOG_LEVEL, validate_required_vars, validate_paths

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def compress_directory(source_path: Path, BACKUP_DESTINATION: Path, timestamp: str) -> Path | None:
    output_path = BACKUP_DESTINATION / f"{source_path.name}_{timestamp}.tar.gz"

    try:
        logger.info(f"Compressing {source_path}")
        subprocess.run(
            ["tar", "-czf", output_path, source_path],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Backup created {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Compressing failed: {e}")
        return None

def backup_validator(output_path: Path) -> tuple[str, float, float] | None:
    if not output_path.exists():
        logger.error("Archive not found")
        return None

    size_bytes = output_path.stat().st_size
    size_mb = output_path.stat().st_size / (1024 * 1024)

    if size_mb <= 0:
        logger.error("Archive size is 0")
        return None

    logger.info(f"Archive size: {size_mb:.2f} MB")

    sha256_hash = hashlib.sha256()

    with output_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)

    checksum = sha256_hash.hexdigest()
    logger.info(f"Checksum: {checksum}")

    return checksum, size_mb, size_bytes

def create_backup_manifest(source_path: Path, output_path: Path, timestamp: str, size_bytes: float, size_mb: float, checksum: str) -> Path | None:
    manifest = {
        "backup_file": str(output_path),
        "source": str(source_path),
        "created": timestamp,
        "size_bytes": size_bytes,
        "size_human": f"{size_mb:.2f} MB",
        "checksum_sha256": checksum
    }

    manifest_file = output_path.with_name(output_path.name.replace(".tar.gz", ".json"))
    with manifest_file.open('w') as f:
        json.dump(manifest, f, indent=4)
    logger.info(f"Manifest created: {manifest_file}")

    return manifest_file

def plan_backup_rotation(
    backup_dir: Path,
    retention_days: int,
    min_backups: int
) -> list[Path]:
    backups = list(backup_dir.glob("*.tar.gz"))

    def get_backup_time(filename: Path):
        name = filename.stem
        name = Path(name).stem
        parts = name.split("_")
        ts = parts[-2] + "_" + parts[-1]
        return datetime.datetime.strptime(ts, "%Y%m%d_%H%M%S")

    backups.sort(key=get_backup_time)

    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)
    remaining = len(backups)
    to_delete = []

    for b in backups:
        if remaining <= min_backups:
            break

        if get_backup_time(b) < cutoff:
            to_delete.append(b)
            remaining -= 1

    return to_delete

def parse_args():
    parser = argparse.ArgumentParser(
        prog="backup.py",
        description="Automated backup tool with compression, rotation, and dry-run support",
        epilog="Example:\n"
               "  python backup.py --dry-run\n"
               "  python backup.py --retention-days 14\n",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--sources",
        nargs="+",
        help="Override backup sources (space-separated paths)"
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        help="Override retention period in days"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate backup process without creating or deleting files"
    )

    return parser.parse_args()

def main():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    success = 0
    failure = 0
    total = 0
    total_size = []

    args = parse_args()
    dry_run = args.dry_run

    logger.info("Starting backup process")

    # ---------- Startup validation ----------
    try:
        validate_required_vars()
        validate_paths()
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False

    sources = args.sources if args.sources else BACKUP_SOURCES
    retention = args.retention_days if args.retention_days is not None else RETENTION_DAYS

    # Normalize sources
    sources = [Path(s) for s in sources]

    if dry_run:
        logger.info("[DRY-RUN MODE] No files will be created or deleted")
        logger.info(f"Backup sources: {sources}")
        logger.info(f"Destination: {BACKUP_DESTINATION}")
        logger.info(f"Retention: {retention} days")

    # ---------- Backup loop ----------
    for source in sources:
        total += 1

        try:
            if dry_run:
                archive_name = f"{source.name}_{timestamp}.tar.gz"
                logger.info(f"[DRY-RUN] Would compress {source}")
                logger.info(f"[DRY-RUN] Would create: {BACKUP_DESTINATION / archive_name}")
                logger.info(f"[DRY-RUN] Would create manifest: {archive_name.replace('.tar.gz', '.json')}")
                success += 1
                continue

            archive = compress_directory(source, BACKUP_DESTINATION, timestamp)
            if archive is None:
                failure += 1
                continue

            validation = backup_validator(archive)
            if validation is None:
                failure += 1
                continue

            checksum, size_mb, size_bytes = validation
            total_size.append(size_mb)

            manifest = create_backup_manifest(
                source,
                archive,
                timestamp,
                size_bytes,
                size_mb,
                checksum
            )

            if manifest is None:
                failure += 1
                continue

            success += 1

        except Exception as e:
            logger.error(f"Unexpected error backing up {source}: {e}")
            failure += 1
            continue

    # ---------- Rotation ----------
    to_delete = plan_backup_rotation(
        BACKUP_DESTINATION,
        retention,
        MIN_BACKUPS
    )

    if dry_run:
        logger.info(f"[DRY-RUN] Found {len(to_delete)} old backups that would be deleted:")
        for b in to_delete:
            logger.info(f"[DRY-RUN]   - {b.name}")
        deleted = len(to_delete)
    else:
        for b in to_delete:
            logger.info(f"Deleting old backup: {b.name}")
            b.unlink()

            manifest = b.with_suffix(".json")
            if manifest.exists():
                manifest.unlink()

        deleted = len(to_delete)

    # ---------- Summary ----------
    sum_sizes = sum(total_size)

    logger.info("=== [DRY-RUN] Backup Summary ===" if dry_run else "=== Backup Summary ===")
    logger.info(f"Total sources: {total}")

    if dry_run:
        logger.info(f"Would create: {success} backups")
        logger.info(f"Would delete: {deleted} old backups")
    else:
        logger.info(f"Successful: {success}")
        logger.info(f"Failed: {failure}")
        logger.info(f"Old backups deleted: {deleted}")
        logger.info(f"Total backup size: {sum_sizes:.2f} MB")

    return True

if __name__ == "__main__":
    main()
