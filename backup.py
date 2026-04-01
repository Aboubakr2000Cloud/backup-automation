#!/usr/bin/env python3
import subprocess
import boto3
import logging
from datetime import datetime, timedelta, timezone
import hashlib
import json
import time
import argparse
from pathlib import Path
from botocore.exceptions import ClientError
from boto3.exceptions import S3UploadFailedError
from config import LOG_FILE, BACKUP_SOURCES, BACKUP_DESTINATION, RETENTION_DAYS, MIN_BACKUPS, LOG_LEVEL, S3_BACKUP_BUCKET, S3_PREFIX, UPLOAD_TO_S3, DELETE_LOCAL_AFTER_UPLOAD, S3_RETENTION_DAYS, validate_required_vars, validate_paths, validate_bucket, validate_s3_config

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

def plan_backup_rotation(backup_dir: Path, retention_days: int, min_backups: int) -> list[Path]:
    backups = list(backup_dir.glob("*.tar.gz"))

    def get_backup_time(filename: Path):
        name = filename.stem
        name = Path(name).stem
        parts = name.split("_")
        ts = parts[-2] + "_" + parts[-1]
        return datetime.strptime(ts, "%Y%m%d_%H%M%S")

    backups.sort(key=get_backup_time)

    cutoff = datetime.now() - timedelta(days=retention_days)
    remaining = len(backups)
    to_delete = []

    for b in backups:
        if remaining <= min_backups:
            break

        if get_backup_time(b) < cutoff:
            to_delete.append(b)
            remaining -= 1

    return to_delete

def upload_archive_s3(s3, archive, bucket, s3_key, checksum, retries=3):
    for attempt in range(1, retries + 1):
        try:
            s3.upload_file(
                str(archive),
                bucket,
                s3_key,
                ExtraArgs={
                    "Metadata": {
                    "sha256": checksum
                    }
                }
            )

            logger.info(f"Uploaded {s3_key}")
            return True

        except (S3UploadFailedError, ClientError) as e:
            logger.warning(f"Attempt {attempt} failed for {s3_key}: {e}")

            if isinstance(e, ClientError):
                code = e.response["Error"]["Code"]
                if code in ["AccessDenied", "NoSuchBucket"]:
                    logger.error(f"Permanent error ({code}) → not retrying")
                    return False

            if attempt == retries:
                logger.error(f"Failed after {retries} attempts: {s3_key}")
                return False

            time.sleep(2 ** attempt) 

        except Exception as e:
            logger.error(f"Unexpected error for {s3_key}: {e}")
            return False

def build_s3_key(S3_PREFIX, archive, dt):
    archive = Path(archive)
    date_path = f"{dt.year}/{dt.month:02d}/{dt.day:02d}/"
    return f"{S3_PREFIX}{date_path}{archive.name}"
    
def verify_s3_upload(s3, bucket, s3_key, checksum):
    try:
        head = s3.head_object(Bucket=bucket, Key=s3_key)

        s3_checksum = head["Metadata"].get("sha256")

        if not s3_checksum:
            logger.error("No checksum metadata found in S3 object")
            return False

        if checksum == s3_checksum:
            logger.info("Uploaded file matches local checksum!")
            return True
        else:
            logger.warning("Uploaded file does NOT match local checksum!")
            return False

    except ClientError as e:
        logger.error(f"Failed to verify S3 upload: {e}")
        return False
        
def plan_s3_rotation(s3, bucket, prefix, retention_days, min_backups, dry_run=False):

    logger.info("Starting S3 backup cleanup...")

    try:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

        if "Contents" not in response:
            logger.info("No backups found in S3.")
            return 0

        objects = [
            obj for obj in response["Contents"]
            if obj["Key"].endswith(".tar.gz")
        ]

        if not objects:
            logger.info("No backup archives found in S3.")
            return 0

        objects.sort(key=lambda obj: obj["LastModified"])

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        remaining_s3 = len(objects)
        to_delete_s3 = []

        for obj in objects:
            if remaining_s3 <= min_backups:
                break

            if obj["LastModified"] < cutoff:
                to_delete_s3.append(obj)
                remaining_s3 -= 1

        return to_delete_s3

    except Exception as e:
        logger.error(f"S3 cleanup failed: {e}")
        return 0        

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
    
    parser.add_argument(
        "--upload",
        action="store_true", 
        dest="upload", 
        help="Force enable S3 upload"
    )
        
    parser.add_argument(
        "--no-upload",
        action="store_false",
        dest="upload",
        help="Disable S3 upload"
    )
    
    parser.add_argument(
        "--delete-local",
        action="store_true",
        help="delete local file"
    )
    
    parser.add_argument(
        "--keep-local",
        action="store_false",
        dest="delete_local",
        help="keep local file"
    )
    
    parser.set_defaults(upload=None)

    return parser.parse_args()

def main():
    dt = datetime.now()
    timestamp = dt.strftime("%Y%m%d_%H%M%S")

    success = 0
    failure = 0
    total = 0
    failed_local_deletions = 0
    failed_s3_deletions = 0
    deleted_s3 = 0
    deleted_locally = 0
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
    
    upload_enabled = args.upload if args.upload is not None else UPLOAD_TO_S3
    delete_local_enabled = args.delete_local if args.delete_local is not None else DELETE_LOCAL_AFTER_UPLOAD
    
    if upload_enabled:
       logger.info("S3 upload is ENABLED")
       validate_s3_config()
       if not dry_run:
           s3 = boto3.client("s3")
           validate_bucket(s3, S3_BACKUP_BUCKET, logger)
    else:
       logger.info("S3 upload is DISABLED")
     
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
                archive = f"{source.name}_{timestamp}.tar.gz"
                s3_key = build_s3_key(S3_PREFIX, archive, dt)
                logger.info(f"[DRY-RUN] Would compress {source}")
                logger.info(f"[DRY-RUN] Would create: {BACKUP_DESTINATION / archive}")
                logger.info(f"[DRY-RUN] Would create manifest: {archive.replace('.tar.gz', '.json')}")
                if upload_enabled:
                   logger.info(f"[DRY-RUN] Would upload {archive} to {S3_BACKUP_BUCKET} S3 bucket: {s3_key}")
                   if delete_local_enabled:
                      logger.info(f"[DRY-RUN] Would delete {archive} and its manifest {archive.replace('.tar.gz', '.json')}")
                      
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

            if upload_enabled:
               s3_key = build_s3_key(S3_PREFIX, archive, dt)
               
               s3 = boto3.client("s3")
               
               upload = upload_archive_s3(s3, archive, S3_BACKUP_BUCKET, s3_key, checksum, retries=3)
               
               if not upload:
                   logger.error(f"Failed to upload {archive.name} to {S3_BACKUP_BUCKET} S3 bucket: {s3_key}")
                   continue
                  
               verify = verify_s3_upload(s3, S3_BACKUP_BUCKET, s3_key, checksum)
               
               if not verify:
                   logger.error(f"Checksum verification failed for {archive.name}")
                   failure += 1
                   continue
                   
               if upload_enabled and delete_local_enabled:
                  logger.info(f"Deleting local backup (verified uploaded): {archive.name}")
                  try:
                     archive.unlink()
                     
                     if manifest and manifest.exists():
                        manifest.unlink()
                        
                     logger.info(f"Deleted local backup and manifest for {archive.name}")
                  except Exception as e:
                     logger.error(f"Failed to delete {archive.name}: {e}")
                     
            success += 1

        except Exception as e:
            logger.error(f"Unexpected error backing up {source}: {e}")
            failure += 1
            continue
            
    # ---------- S3 Rotation ----------
            
    if upload_enabled:
       if dry_run:
          logger.info("[DRY-RUN] Would perform S3 cleanup (skipped, no AWS calls)")
       else:
            s3 = boto3.client("s3")
       
            to_delete_s3 = plan_s3_rotation(s3, S3_BACKUP_BUCKET, S3_PREFIX, S3_RETENTION_DAYS, MIN_BACKUPS, dry_run=False)
       
            for obj in to_delete_s3:
                key = obj["Key"]
                logger.info(f"Deleting old S3 backup: {key}")

                try:
                    s3.delete_object(Bucket=S3_BACKUP_BUCKET, Key=key)

                    manifest_key = key.replace(".tar.gz", ".json")
                    try:
                        s3.delete_object(Bucket=S3_BACKUP_BUCKET, Key=manifest_key)
                    except Exception:
                       pass 

                    deleted_s3 += 1

                except Exception as e:
                    logger.error(f"Failed to delete {key}: {e}")
                 
                    failed_s3_deletions += 1

            
    # ---------- Local Rotation ----------
    
    to_delete_locally = plan_backup_rotation(BACKUP_DESTINATION, RETENTION_DAYS, MIN_BACKUPS)

    if dry_run:
        logger.info(f"[DRY-RUN] Found {len(to_delete_locally)} old local backups that would be deleted:")
        for b in to_delete_locally:
            logger.info(f"[DRY-RUN]   - {b.name}")
        deleted_locally = len(to_delete_locally)
    else:
        for b in to_delete_locally:
            logger.info(f"Deleting old backup: {b.name}")
            try:
                b.unlink()

                manifest = b.with_name(b.name.replace(".tar.gz", ".json"))
                if manifest.exists():
                   manifest.unlink()
                   logger.info(f"Deleted manifest: {manifest.name}")

                deleted_locally += 1
            
            except Exception as e:
                logger.error(f"Failed to delete {b.name}: {e}")
                
                failed_local_deletions += 1

    # ---------- Summary ----------
    sum_sizes = sum(total_size)

    logger.info("=== [DRY-RUN] Backup Summary ===" if dry_run else "=== Backup Summary ===")
    logger.info(f"Total sources: {total}")

    if dry_run:
        logger.info(f"Would create: {success} backups")
        logger.info(f"Would delete: {deleted_locally} old local backups")
    else:
        logger.info(f"Successful: {success}")
        logger.info(f"Failed: {failure}")
        logger.info(f"Old local backups deleted: {deleted_locally}")
        logger.info(f"Old s3 backups deleted: {deleted_s3}")
        logger.info(f"Failed local deletions: {failed_local_deletions}")
        logger.info(f"Failed s3 deletions: {failed_s3_deletions}")
        logger.info(f"Total backup size: {sum_sizes:.2f} MB")

    return True

if __name__ == "__main__":
    main()
