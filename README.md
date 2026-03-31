# Week 8 — Automation & Integrations

## Overview

This week focused on Python-shell integration and building production-ready automation systems. The project demonstrates automated backup workflows with compression, validation, intelligent rotation, upload to S3 and comprehensive error handling.

**Key Learning Areas:**
- Running shell commands from Python using `subprocess`
- File compression with tar/gzip
- Backup validation with SHA256 checksums
- Intelligent backup rotation strategies
- Upload to S3
- Environment variable management
- CLI tool development with argparse
- Production-ready logging and error handling

---

## Project: Automated Backup & Rotation System

A professional command-line backup automation tool that compresses directories, validates archives, manages backup retention, uploads to S3 and provides detailed logging. Built with reliability and maintainability in mind.

### Project Structure

```
week8-backup-automation/
│
├── backup.py              # Main backup script
├── config.py              # Configuration and validation
├── .env                   # Environment variables (not in Git)
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── README.md             # This file
│
├── logs/                 # Application logs
│   └── backup.log
│
└── backups/              # Backup destination
    ├── folder1_20250208_143022.tar.gz
    ├── folder1_20250208_143022.json
    ├── folder2_20250208_143025.tar.gz
    └── folder2_20250208_143025.json
```

---

## Features

✅ **Multi-Source Backup** - Compress multiple directories in a single run  
✅ **Timestamped Archives** - Unique filenames with precise timestamps  
✅ **Backup Validation** - Verify archives with SHA256 checksums  
✅ **JSON Manifests** - Metadata files for each backup (size, checksum, timestamp)  
✅ **Intelligent Rotation** - Delete old backups while keeping minimum count  
✅ **Dry-Run Mode** - Preview operations without creating/deleting files  
✅ **CLI Overrides** - Command-line arguments override .env settings  
✅ **Comprehensive Logging** - Dual output (file + console) with timestamps  
✅ **Error Resilience** - Continue processing on single source failure  
✅ **Detailed Summary** - Statistics on success/failure/deletions
✅ **S3 Cloud Upload** - Upload backups to AWS S3 with verification  
✅ **Dual Retention** - Separate policies for local and S3 storage  
✅ **Date-Organized S3 Storage** - Backups organized by year/month/day  
✅ **Upload Verification** - SHA256 checksum validation after upload  
✅ **Optional Local Cleanup** - Delete local files after verified S3 upload  
✅ **S3 Rotation** - Automatic cleanup of old cloud backups

---

## Installation

### Prerequisites

- Python 3.10+
- Linux/macOS (tar command required)
- Read access to backup sources
- Write access to backup destination

### Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd week8-backup-automation
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the project root:

```bash
# .env
BACKUP_SOURCES=/path/to/folder1,/path/to/folder2,/path/to/folder3
BACKUP_DESTINATION=/path/to/backups
RETENTION_DAYS=7
MIN_BACKUPS_TO_KEEP=3
S3_BACKUP_BUCKET=my-bucket
S3_PREFIX=backups/
UPLOAD_TO_S3=false
DELETE_LOCAL_AFTER_UPLOAD=false
S3_RETENTION_DAYS=30
LOG_LEVEL=INFO
```

**Configuration Options:**

| Variable | Description | Example |
|----------|-------------|---------|
| `BACKUP_SOURCES` | Comma-separated paths to backup | `/home/user/projects,/home/user/docs` |
| `BACKUP_DESTINATION` | Where to save archives | `/home/user/backups` |
| `RETENTION_DAYS` | Delete backups older than N days | `7` |
| `MIN_BACKUPS_TO_KEEP` | Minimum backups to retain (even if old) | `3` |
| `S3_BACKUP_BUCKET` | S3 bucket | `My bucket` |
| `S3_PREFIX` | S3 prefix | `backups/` |
| `UPLOAD_TO_S3` | Action to upload to S3 | `true / false` |
| `DELETE_LOCAL_AFTER_UPLOAD` | Action to delete local file after being uploaded | `true / false` |
| `S3_RETENTION_DAYS` | Delete S3 backups older than N days | `30` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

5. **Create required directories**
```bash
mkdir -p logs backups
```

---

## Usage

### Basic backup

Run with default settings from `.env`:

```bash
python backup.py
```

**Output:**
```
2025-02-08 14:30:22 - INFO - Starting backup process
2025-02-08 14:30:22 - INFO - Configuration loaded successfully
2025-02-08 14:30:23 - INFO - Compressing /home/user/projects
2025-02-08 14:30:25 - INFO - Backup created /home/user/backups/projects_20250208_143025.tar.gz
2025-02-08 14:30:25 - INFO - Archive size: 15.32 MB
2025-02-08 14:30:26 - INFO - Checksum: a3f5c89b2e1d4f...
2025-02-08 14:30:26 - INFO - Manifest created: projects_20250208_143025.json
2025-02-08 14:30:27 - INFO - Deleting old backup: projects_20250201_120000.tar.gz
2025-02-08 14:30:27 - INFO - === Backup Summary ===
2025-02-08 14:30:27 - INFO - Total sources: 3
2025-02-08 14:30:27 - INFO - Successful: 3
2025-02-08 14:30:27 - INFO - Failed: 0
2025-02-08 14:30:27 - INFO - Old backups deleted: 2
2025-02-08 14:30:27 - INFO - Total backup size: 42.18 MB
```

### Command-Line Options

**Override backup sources:**
```bash
python backup.py --sources /tmp/test /home/user/docs
```

**Override retention period:**
```bash
python backup.py --retention-days 14
```

**Combine options:**
```bash
python backup.py --sources /home/user/important --retention-days 30
```

**Dry-run mode (preview without changes):**
```bash
python backup.py --dry-run
```

**Dry-run output:**
```
2025-02-08 14:35:00 - INFO - [DRY-RUN MODE] No files will be created or deleted
2025-02-08 14:35:00 - INFO - Backup sources: [PosixPath('/home/user/projects')]
2025-02-08 14:35:00 - INFO - Destination: /home/user/backups
2025-02-08 14:35:00 - INFO - Retention: 7 days
2025-02-08 14:35:01 - INFO - [DRY-RUN] Would compress /home/user/projects
2025-02-08 14:35:01 - INFO - [DRY-RUN] Would create: /home/user/backups/projects_20250208_143501.tar.gz
2025-02-08 14:35:01 - INFO - [DRY-RUN] Would create manifest: projects_20250208_143501.json
2025-02-08 14:35:02 - INFO - [DRY-RUN] Found 2 old backups that would be deleted:
2025-02-08 14:35:02 - INFO - [DRY-RUN]   - projects_20250125_120000.tar.gz
2025-02-08 14:35:02 - INFO - [DRY-RUN]   - projects_20250128_120000.tar.gz
2025-02-08 14:35:02 - INFO - === [DRY-RUN] Backup Summary ===
2025-02-08 14:35:02 - INFO - Total sources: 1
2025-02-08 14:35:02 - INFO - Would create: 1 backups
2025-02-08 14:35:02 - INFO - Would delete: 2 old backups
```

### S3 Upload

**Enable S3 upload:**
```bash
python backup.py --upload
```

**Disable S3 upload:**
```bash
python backup.py --no-upload
```

**Upload and delete local after verification:**
```bash
python backup.py --upload --delete-local
```

**Configuration (.env):**
```
UPLOAD_TO_S3=true
S3_BACKUP_BUCKET=my-abou-backup-bucket
S3_PREFIX=backups/
S3_RETENTION_DAYS=30
DELETE_LOCAL_AFTER_UPLOAD=false
```

**View help:**
```bash
python backup.py --help
```

**Backup with upload Output:**

```
2026-03-31 16:16:02,796 - INFO - Starting backup process
2026-03-31 16:16:02,804 - INFO - Configuration loaded successfully
2026-03-31 16:16:02,804 - INFO - S3 upload is ENABLED
2026-03-31 16:16:02,863 - INFO - Found credentials in shared credentials file: ~/.aws/credentials
2026-03-31 16:16:04,482 - INFO - Bucket 'my-abou-backups-bucket' is accessible
2026-03-31 16:16:04,483 - INFO - Compressing /home/abou/S3_folder
2026-03-31 16:16:04,607 - INFO - Backup created /home/abou/backups/S3_folder_20260331_161602.tar.gz
2026-03-31 16:16:04,610 - INFO - Archive size: 0.00 MB
2026-03-31 16:16:04,611 - INFO - Checksum: 9306a3843672dba3df3e2ebcc3da4381cb00af1a35d68e2a0f1ef3ddfc0827b1
2026-03-31 16:16:04,612 - INFO - Manifest created: /home/abou/backups/S3_folder_20260331_161602.json
2026-03-31 16:16:05,381 - INFO - Uploaded backups/2026/03/31/S3_folder_20260331_161602.tar.gz
2026-03-31 16:16:05,493 - INFO - Uploaded file matches local checksum!
2026-03-31 16:16:05,493 - INFO - Compressing /home/abou/cloud-learning-project/scripts/python
2026-03-31 16:16:05,667 - INFO - Backup created /home/abou/backups/python_20260331_161602.tar.gz
2026-03-31 16:16:05,669 - INFO - Archive size: 0.01 MB
2026-03-31 16:16:05,670 - INFO - Checksum: d0207586e01c9b3979b5b8fa017b561110dbfe9fd9f666d504dbcffe2bb80153
2026-03-31 16:16:05,673 - INFO - Manifest created: /home/abou/backups/python_20260331_161602.json
2026-03-31 16:16:06,640 - INFO - Uploaded backups/2026/03/31/python_20260331_161602.tar.gz
2026-03-31 16:16:06,733 - INFO - Uploaded file matches local checksum!
2026-03-31 16:16:06,821 - INFO - Starting S3 backup cleanup...
2026-03-31 16:16:07,502 - INFO - === Backup Summary ===
2026-03-31 16:16:07,503 - INFO - Total sources: 2
2026-03-31 16:16:07,504 - INFO - Successful: 2
2026-03-31 16:16:07,504 - INFO - Failed: 0
2026-03-31 16:16:07,504 - INFO - Old local backups deleted: 0
2026-03-31 16:16:07,504 - INFO - Old s3 backups deleted: 0
2026-03-31 16:16:07,504 - INFO - Failed local deletions: 0
2026-03-31 16:16:07,504 - INFO - Failed s3 deletions: 0
2026-03-31 16:16:07,504 - INFO - Total backup size: 0.01 MB
```

**Dry-run with upload simulation output :**

```
2026-03-31 16:26:51,014 - INFO - Starting backup process
2026-03-31 16:26:51,014 - INFO - Configuration loaded successfully
2026-03-31 16:26:51,015 - INFO - S3 upload is ENABLED
2026-03-31 16:26:51,015 - INFO - [DRY-RUN MODE] No files will be created or deleted
2026-03-31 16:26:51,015 - INFO - Backup sources: [PosixPath('/home/abou/S3_folder'), PosixPath('/home/abou/cloud-learning-project/scripts/python')]
2026-03-31 16:26:51,015 - INFO - Destination: /home/abou/backups
2026-03-31 16:26:51,015 - INFO - Retention: 6 days
2026-03-31 16:26:51,015 - INFO - [DRY-RUN] Would compress /home/abou/S3_folder
2026-03-31 16:26:51,016 - INFO - [DRY-RUN] Would create: /home/abou/backups/S3_folder_20260331_162651.tar.gz
2026-03-31 16:26:51,016 - INFO - [DRY-RUN] Would create manifest: S3_folder_20260331_162651.json
2026-03-31 16:26:51,016 - INFO - [DRY-RUN] Would upload S3_folder_20260331_162651.tar.gz to my-abou-backups-bucket S3 bucket: backups/2026/03/31/S3_folder_20260331_162651.tar.gz
2026-03-31 16:26:51,016 - INFO - [DRY-RUN] Would compress /home/abou/cloud-learning-project/scripts/python
2026-03-31 16:26:51,016 - INFO - [DRY-RUN] Would create: /home/abou/backups/python_20260331_162651.tar.gz
2026-03-31 16:26:51,016 - INFO - [DRY-RUN] Would create manifest: python_20260331_162651.json
2026-03-31 16:26:51,016 - INFO - [DRY-RUN] Would upload python_20260331_162651.tar.gz to my-abou-backups-bucket S3 bucket: backups/2026/03/31/python_20260331_162651.tar.gz
2026-03-31 16:26:51,016 - INFO - [DRY-RUN] Would perform S3 cleanup (skipped, no AWS calls)
2026-03-31 16:26:51,022 - INFO - [DRY-RUN] Found 0 old local backups that would be deleted:
2026-03-31 16:26:51,023 - INFO - === [DRY-RUN] Backup Summary ===
2026-03-31 16:26:51,023 - INFO - Total sources: 2
2026-03-31 16:26:51,023 - INFO - Would create: 2 backups
2026-03-31 16:26:51,023 - INFO - Would delete: 0 old local backups

```
---

## How It Works

### 1. Configuration Validation
- Loads environment variables from `.env`
- Validates all required variables exist
- Checks source directories exist and are readable
- Ensures destination is writable
- Creates destination directory if needed

### 2. Backup Creation
- Generates timestamp: `YYYYMMDD_HHMMSS`
- Compresses each source using `tar -czf`
- Creates `.tar.gz` archive with format: `{folder}_{timestamp}.tar.gz`
- Logs compression progress

### 3. Backup Validation
- Verifies archive exists
- Checks file size > 0
- Calculates SHA256 checksum
- Logs validation results

### 4. Manifest Creation
- Creates JSON metadata file
- Includes: filename, source, timestamp, size, checksum
- Saves alongside archive with `.json` extension

**Example Manifest:**
```json
{
    "backup_file": "/home/user/backups/projects_20250208_143025.tar.gz",
    "source": "/home/user/projects",
    "created": "20250208_143025",
    "size_bytes": 16065536,
    "size_human": "15.32 MB",
    "checksum_sha256": "a3f5c89b2e1d4f6c3a8e9b5d2f1a7c4e6b8d3f5a9c2e7b4d1f8a6c3e9b5d2f1a"
}
```

### 5. Uploads to S3 (Optional)
- If enabled, uploads verified backups to S3

### 6. Verifies S3 Upload
- Checks uploaded file matches local checksum

### 7. Organizes S3 Backups
- Stores in date-based structure (2025/02/10/)

### 8. Cleans S3 Backups
- Deletes S3 backups older than S3_RETENTION_DAYS

### 9. Optional Local Cleanup
- Deletes local copy after verified S3 upload
  
### 10. local backup Rotation
- Lists all `.tar.gz` files in destination
- Parses timestamps from filenames
- Identifies backups older than `RETENTION_DAYS`
- **Always keeps at least `MIN_BACKUPS_TO_KEEP`** (even if old)
- Deletes both archive and manifest for old backups
- Logs each deletion

**Rotation Logic:**
```python
# Example: 10 backups, RETENTION_DAYS=7, MIN_BACKUPS=3
# Scenario 1: 8 are old → deletes 7 (keeps 3)
# Scenario 2: 2 are old → deletes 2 (keeps 8)
# Scenario 3: All 10 are old → deletes 7 (keeps 3)
```

### 11. Summary Report
- Total sources processed
- Successful backups
- Failed backups
- Old local backups deleted
- Old S3 backups deleted
- Failed local deletions
- Failed S3 deletions
- Total backup size created

---

## Output Files

### Archive Files
**Format:** `{folder_name}_{YYYYMMDD_HHMMSS}.tar.gz`

Example: `projects_20250208_143025.tar.gz`

### Manifest Files
**Format:** `{folder_name}_{YYYYMMDD_HHMMSS}.json`

Example: `projects_20250208_143025.json`

Contains metadata for verification and tracking.

### Log File
**Location:** `logs/backup.log`

Persistent log of all operations with timestamps.

---

## Error Handling

### Configuration Errors
```
❌ Missing required environment variables: BACKUP_SOURCES
❌ Backup source does not exist: /nonexistent
❌ Backup source not readable: /protected
❌ Backup destination not writable: /readonly
```

**Behavior:** Script exits immediately with clear error message.

### Backup Errors
```
❌ Compressing failed: [Errno 2] No such file or directory
❌ Archive not found
❌ Archive size is 0
```

**Behavior:** Logs error, marks source as failed, continues to next source.

### Rotation Errors
- Handles missing manifest files gracefully
- Skips rotation if no old backups found
- Continues even if individual deletions fail

---

## Skills Demonstrated

✅ **subprocess Integration** - Running shell commands from Python  
✅ **File Compression** - Creating tar.gz archives programmatically  
✅ **Cryptographic Hashing** - SHA256 checksum calculation  
✅ **JSON Serialization** - Creating structured metadata files  
✅ **Path Manipulation** - Using pathlib for cross-platform paths  
✅ **Timestamp Parsing** - Extracting dates from filenames  
✅ **Backup Rotation Logic** - Implementing retention policies  
✅ **CLI Development** - argparse with help text and overrides  
✅ **Environment Variables** - Configuration management with .env  
✅ **Production Logging** - Dual output with appropriate log levels  
✅ **Error Handling** - Graceful degradation on failures  
✅ **Type Hints** - Modern Python type annotations  
✅ **boto3 S3 Operations** - Upload, list, delete, metadata  
✅ **AWS Error Handling** - ClientError classification and retry logic  
✅ **Data Integrity** - Checksum storage and verification  
✅ **Cloud Storage Patterns** - Date-based organization, dual retention

---

## Technical Highlights

### 1. Intelligent Rotation Algorithm
```python
def plan_backup_rotation(backup_dir, retention_days, min_backups):
    # Sorts by time, respects minimum, only deletes old backups
    # Prevents accidental deletion of all backups
```

**Why It's Smart:**
- Never goes below minimum backup count
- Even if all backups are ancient, keeps the newest N
- Protects against misconfiguration

### 2. Separation of Concerns
```python
compress_directory()      # Creates archive
backup_validator()        # Verifies archive
create_backup_manifest()  # Records metadata
plan_backup_rotation()    # Determines what to delete
```

Each function has single responsibility - testable and maintainable.

### 3. Configuration Validation at Startup
```python
validate_required_vars()  # Ensures all config exists
validate_paths()          # Checks filesystem permissions
```

Fail fast with clear errors instead of cryptic failures mid-execution.

### 4. Dry-Run Pattern
```python
if dry_run:
    logger.info("[DRY-RUN] Would compress {source}")
else:
    compress_directory(source)
```

Industry-standard pattern for safe testing of destructive operations.

### 5. S3 Integration with Verification
```python
# Upload with checksum in metadata
s3.upload_file(
    str(archive),
    bucket,
    s3_key,
    ExtraArgs={"Metadata": {"sha256": checksum}}
)

# Verify upload
head = s3.head_object(Bucket=bucket, Key=s3_key)
if checksum == head["Metadata"]["sha256"]:
    # Upload verified!
```
Stores checksum in S3 metadata for integrity verification.

### 6. Date-Organized S3 Structure
```python
def build_s3_key(prefix, archive, dt):
    date_path = f"{dt.year}/{dt.month:02d}/{dt.day:02d}/"
    return f"{prefix}{date_path}{archive.name}"
```
Production pattern: backups/2025/02/10/backup_143022.tar.gz

### 7. Dual Rotation Logic
- Local rotation: Based on file creation timestamp
- S3 rotation: Based on LastModified attribute
- Different retention policies for local vs cloud

---

## Testing

### Test Scenarios

**1. Basic Functionality**
```bash
# Create test directories
mkdir -p /tmp/test1 /tmp/test2
echo "test" > /tmp/test1/file.txt

# Configure .env
BACKUP_SOURCES=/tmp/test1,/tmp/test2
BACKUP_DESTINATION=/tmp/backups

# Run backup
python backup.py

# Verify: Check /tmp/backups for .tar.gz and .json files
```

**2. Dry-Run Mode**
```bash
python backup.py --dry-run
# Verify: No files created in backups/
```

**3. Rotation Logic**
```bash
# Create 10 backups manually (old timestamps)
# Run backup with MIN_BACKUPS_TO_KEEP=3
# Verify: Only 4 backups remain (3 old + 1 new)
```

**4. Error Handling**
```bash
# Test with non-existent source
python backup.py --sources /nonexistent /tmp/test1
# Verify: Continues processing, logs error
```

**5. CLI Overrides**
```bash
python backup.py --retention-days 1
# Verify: Uses 1 day instead of .env value
```

---

## Troubleshooting

### "Missing required environment variables"
**Solution:** Create `.env` file with all required variables.

### "Backup source does not exist"
**Solution:** Verify paths in `BACKUP_SOURCES` are correct and absolute.

### "Backup destination not writable"
**Solution:** Check permissions on `BACKUP_DESTINATION` directory.

### "Compressing failed"
**Solution:** Ensure `tar` command is available (`which tar`).

### No backups deleted during rotation
**Solution:** Check if backups are actually older than `RETENTION_DAYS`.

---

## Future Enhancements

Potential additions for learning or production use:

- [ ] **Email Notifications** on success/failure
- [ ] **Compression Level Selection** (speed vs size tradeoff)
- [ ] **Parallel Compression** (multiple sources simultaneously)
- [ ] **Database Backup Support** (MySQL, PostgreSQL dumps)
- [ ] **Backup Encryption** (GPG encryption)
- [ ] **Web Dashboard** (view backup history)
- [ ] **Scheduling Integration** (systemd timers, cron)

---

## Project Files

**`backup.py`** - Main script with backup logic and CLI  
**`config.py`** - Configuration loading and validation  
**`.env`** - Environment variables (not committed)  
**`requirements.txt`** - Python dependencies  
**`.gitignore`** - Excludes logs, backups, .env  
**`logs/backup.log`** - Application log file  
**`backups/`** - Backup destination directory  

---

## Dependencies

```
python-dotenv==1.0.0
```

No other external dependencies required! Uses Python standard library:
- `subprocess` - Shell command execution
- `logging` - Application logging
- `datetime` - Timestamp handling
- `hashlib` - SHA256 checksums
- `json` - Manifest serialization
- `pathlib` - Path operations
- `argparse` - CLI parsing
- `boto3` - S3 operations

---

## Security Considerations

🔒 **Never commit `.env` files** - Contains sensitive paths  
🔒 **Validate all paths** - Prevent directory traversal  
🔒 **Check permissions** - Ensure read/write access before operations  
🔒 **Use absolute paths** - Avoid ambiguity with relative paths  
🔒 **Sanitize inputs** - Especially if accepting user paths  

---

**Week 8 Complete!** This project demonstrates production-ready automation patterns used in real DevOps workflows. The skills acquired—subprocess execution, file compression, backup rotation, and CLI development—are fundamental to infrastructure automation and system administration.
