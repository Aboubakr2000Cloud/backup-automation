# Week 8 — Learning Notes: Automation & Integrations

## Overview

This week marked a major shift from "scripts that work once" to **production-ready automation systems**. Focus areas included subprocess execution, file compression, backup validation, intelligent rotation logic, and building fault-tolerant automation tools.

---

## 1️⃣ Automation Thinking - The Big Shift

### What I Learned

**Mindset change:**
- FROM: "Write a script that works once"
- TO: "Design a reusable, safe, configurable automation tool"

**Key principle:** Automation is about **repeatability, safety, and predictability** — not just code execution.

### Code Example

```python
# ❌ Beginner approach: Hardcoded, runs once
subprocess.run(['tar', '-czf', 'backup.tar.gz', '/home/user/data'])

# ✅ Production approach: Configurable, validated, logged
def compress_directory(source, destination, timestamp):
    output = destination / f"{source.name}_{timestamp}.tar.gz"
    try:
        logger.info(f"Compressing {source}")
        subprocess.run(['tar', '-czf', output, source], check=True)
        return output
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        return None
```

---

## 2️⃣ subprocess - Running Shell Commands from Python

### What I Learned

**How to execute shell commands programmatically:**
- Use `subprocess.run()` for command execution
- Capture output with `capture_output=True, text=True`
- Handle errors with `check=True` (raises exception on failure)
- Set timeouts to prevent hanging
- Use list format for commands (safer than `shell=True`)

### Key Concepts

**Important parameters:**
- `check=True` → Auto-raise exception on non-zero exit code
- `capture_output=True` → Capture stdout/stderr
- `text=True` → Return strings instead of bytes
- `timeout=N` → Kill command if takes too long

### Code Example

```python
import subprocess

# Basic command execution
result = subprocess.run(
    ['tar', '-czf', 'backup.tar.gz', 'folder/'],
    capture_output=True,
    text=True,
    check=True,
    timeout=300
)

# Access results
print(result.returncode)  # 0 = success
print(result.stdout)      # Command output
print(result.stderr)      # Error messages
```

---

## 3️⃣ File Compression & Archiving

### What I Learned

**Creating tar.gz archives:**
- Use `tar -czf` for compress + archive
- Naming conventions affect rotation and parsing
- Timestamp consistency is critical
- Return the path to the archive for chaining operations

**Key insight:** Compression is not the goal — it's a step in a pipeline.

### Code Example

```python
import subprocess
from pathlib import Path

def create_backup(source, destination, timestamp):
    archive_name = f"{source.name}_{timestamp}.tar.gz"
    archive_path = destination / archive_name
    
    subprocess.run(
        ['tar', '-czf', str(archive_path), str(source)],
        check=True
    )
    
    return archive_path  # Return for next step (validation, manifest)
```

---

## 4️⃣ Backup Validation & Integrity

### What I Learned

**Critical concept:** Checksums are digital fingerprints
- SHA256 creates unique hash for file contents
- Hash the archive itself, not individual files
- Use binary reading (`rb`) for all file types
- Read in chunks for large files (memory efficiency)

**Why it matters:** Validate backups programmatically, not visually.

### Code Example

```python
import hashlib

def calculate_checksum(filepath):
    """Calculate SHA256 checksum for backup validation"""
    sha256 = hashlib.sha256()
    
    with open(filepath, 'rb') as f:
        # Read in 4KB chunks (memory efficient)
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    
    return sha256.hexdigest()
```

### Why Chunked Reading?

- Large files (GBs) don't fit in memory
- `iter(lambda: f.read(4096), b"")` reads until empty bytes
- Standard pattern for processing large files

---

## 5️⃣ Configuration Management

### What I Learned

**Separate concerns:**
1. **Raw values** (from `.env`)
2. **Validated values** (after checks)
3. **Fail fast** on invalid config

**Key decision:** What should crash startup vs continue per-source?
- Missing config → crash immediately
- Bad source path → skip that source, continue

### Code Example

```python
# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_SOURCES = os.getenv('BACKUP_SOURCES')

def validate_required_vars():
    """Fail fast if config missing"""
    if not RAW_SOURCES:
        raise RuntimeError("Missing BACKUP_SOURCES in .env")

# Parse and validate
BACKUP_SOURCES = [Path(p.strip()) for p in RAW_SOURCES.split(',')]

def validate_paths():
    """Check filesystem access"""
    for src in BACKUP_SOURCES:
        if not src.is_dir():
            raise ValueError(f"Source does not exist: {src}")
        if not os.access(src, os.R_OK):
            raise PermissionError(f"Source not readable: {src}")
```

**Rule:** Validate the runtime environment, not just the config file.

---

## 6️⃣ Backup Rotation Logic

### What I Learned

**Rotation is complex:**
- Not just "delete old files"
- Combination of time-based rules + count-based safety
- Must ALWAYS keep minimum number of backups
- Deletion must be sorted (oldest first), controlled, predictable

**Critical insight:** A wrong rotation script can destroy data.

### Code Example

```python
def plan_backup_rotation(backup_dir, retention_days, min_backups):
    """Determine which backups to delete (planning phase)"""
    backups = list(backup_dir.glob("*.tar.gz"))
    backups.sort(key=get_backup_time)  # Oldest first
    
    cutoff = datetime.now() - timedelta(days=retention_days)
    remaining = len(backups)
    to_delete = []
    
    for backup in backups:
        # Safety check: never go below minimum
        if remaining <= min_backups:
            break
        
        # Only delete if old
        if get_backup_time(backup) < cutoff:
            to_delete.append(backup)
            remaining -= 1
    
    return to_delete  # Return list, don't delete yet
```

**Pattern:** Separate **planning** (what to delete) from **execution** (actually deleting).

---

## 7️⃣ Dry-Run Mode - Professional Feature

### What I Learned

**Dry-run must:**
- Simulate exactly, not approximately
- Show what WOULD happen
- Use the SAME logic as real execution
- Never lie about what it would do

**Pattern:** Planner/Executor separation
- Planner: Decides what to do (used by both modes)
- Executor: Does it or logs it (depends on dry-run flag)

### Code Example

```python
def main():
    dry_run = args.dry_run
    
    # Planning phase (same for both modes)
    to_delete = plan_backup_rotation(backup_dir, retention_days, min_backups)
    
    # Execution phase (different behavior)
    if dry_run:
        logger.info(f"[DRY-RUN] Would delete {len(to_delete)} backups")
        for backup in to_delete:
            logger.info(f"[DRY-RUN]   - {backup.name}")
    else:
        for backup in to_delete:
            logger.info(f"Deleting {backup.name}")
            backup.unlink()
```

**Why this matters:** Duplicating logic is dangerous — dry-run could lie.

---

## 8️⃣ Error Handling & Fault Tolerance

### What I Learned

**Production-grade pattern:**
- One folder fails → others continue
- One backup fails → summary still generated
- Errors are logged, counted, and isolated

**Key insight:** Systems fail partially, not completely.

### Code Example

```python
success = 0
failure = 0

for source in sources:
    try:
        archive = compress_directory(source, destination, timestamp)
        if archive:
            success += 1
        else:
            failure += 1
    except Exception as e:
        logger.error(f"Failed to backup {source}: {e}")
        failure += 1
        continue  # Don't stop, process next source

# Always show summary, even if some failed
logger.info(f"Successful: {success}, Failed: {failure}")
```

---

## 9️⃣ CLI Design with argparse

### What I Learned

**How CLI overrides work:**
- CLI flags override `.env` defaults
- Use `is not None` instead of truthiness
- Provide meaningful `--help` output

### Code Example

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Backup automation tool")
    parser.add_argument('--sources', nargs='+', help='Override backup sources')
    parser.add_argument('--retention-days', type=int, help='Override retention')
    parser.add_argument('--dry-run', action='store_true', help='Simulate only')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Use CLI if provided, else config
    sources = args.sources if args.sources else BACKUP_SOURCES
    retention = args.retention_days if args.retention_days is not None else RETENTION_DAYS
```

**Bug I fixed:** `if args.retention_days` fails when value is 0! Use `is not None`.

---

## 🔟 Logging & Observability

### What I Learned

**Logging principles:**
- Logs explain what happened AND why
- Support debugging after the fact
- Professional logs vs student `print()` statements

**Structure matters:**
- Start with context (config loaded)
- Log progress (compressing X)
- Log results (success/failure)
- End with summary (stats)

### Code Example

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Log with context
logger.info(f"Compressing {source.name}")
logger.info(f"Archive created: {archive.name}")
logger.error(f"Compression failed: {error}")
```

---

## ⚠️ Key Challenges & Solutions

### Challenge 1: Timestamp Parsing Bugs
**Problem:** Creation format didn't match parsing format  
**Solution:** Enforced single timestamp standard (`%Y%m%d_%H%M%S`)  
**Lesson:** Naming conventions are part of your API

### Challenge 2: `datetime.datetime.datetime` Error
**Problem:** Conflicting imports  
**Solution:** Use `import datetime` consistently  
**Lesson:** Ambiguous imports cause subtle bugs

### Challenge 3: Manifest Naming (`.tar.json` bug)
**Problem:** `with_suffix()` only replaces ONE suffix  
**Solution:** Explicitly replace `.tar.gz` → `.json`  
**Lesson:** Filesystem APIs have sharp edges

### Challenge 4: Dry-Run Lying About Deletions
**Problem:** Dry-run counted all backups as deletable  
**Solution:** Reused real rotation logic via planner function  
**Lesson:** Dry-run must be truthful

### Challenge 5: CLI Override Not Working
**Problem:** `args.retention_days` ignored when 0  
**Solution:** Check `is not None` instead of truthiness  
**Lesson:** CLI parsing bugs are logic bugs

---

## Week 8 Summary

### Skills Acquired

- [x] Running shell commands from Python (subprocess)
- [x] File compression and archiving (tar.gz)
- [x] Backup validation with checksums (SHA256)
- [x] Intelligent backup rotation logic
- [x] Configuration validation and error handling
- [x] CLI tool development (argparse)
- [x] Dry-run mode implementation
- [x] Production-ready logging patterns
- [x] Fault-tolerant automation design

### Key Takeaways

1. **Automation is about safety first** - Wrong scripts destroy data
2. **Validation happens at multiple stages** - Config, filesystem, backups
3. **Separation of concerns matters** - Planning vs execution
4. **Errors should be isolated** - One failure shouldn't stop everything
5. **Dry-run mode must be truthful** - Reuse logic, don't duplicate

### What I'm Most Proud Of

- Implementing intelligent rotation that respects minimum backup count
- Designing planner/executor separation for dry-run
- Building fault-tolerant pipeline (one source fails, others continue)
- Production-quality logging and error messages
- CLI that meaningfully overrides config

---

## Real-World Applications

**This week's skills directly apply to:**
- Automated database backups
- Log rotation systems
- Configuration management
- CI/CD pipelines
- Disaster recovery automation
- Infrastructure maintenance scripts

**Pattern I learned:** Real automation tools are 20% core logic, 80% safety, validation, and error handling.

---

## What This Means

After this week, I can confidently build automation scripts that:
- Run safely in production (cron, servers, CI)
- Handle failures gracefully
- Provide meaningful feedback
- Are configurable without code changes
- Can be tested without risk (dry-run)

---

**Week 8 Complete!** 
