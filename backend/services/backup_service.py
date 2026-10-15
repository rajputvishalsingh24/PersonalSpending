import os
import sqlite3
import datetime
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.config import DB_PATH, BACKUP_DIR, MAX_BACKUP_RETENTION

logger = logging.getLogger("spendsense.backup")

def create_database_backup() -> Dict[str, Any]:
    """
    Perform an online, atomic SQLite database backup using conn.backup().
    Validates integrity before and after backup, and applies rotation retention.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found at {DB_PATH}")

    # 1. Check live database integrity
    live_conn = sqlite3.connect(DB_PATH)
    try:
        check = live_conn.execute("PRAGMA integrity_check;").fetchone()[0]
        if check != "ok":
            raise ValueError(f"Source database failed integrity check: {check}")

        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"spendsense_backup_{timestamp}.db"
        backup_path = BACKUP_DIR / backup_filename

        # 2. Perform online backup safely
        backup_conn = sqlite3.connect(backup_path)
        try:
            live_conn.backup(backup_conn, pages=100)
        finally:
            backup_conn.close()

    finally:
        live_conn.close()

    # 3. Verify integrity of the created backup file
    verify_conn = sqlite3.connect(backup_path)
    try:
        verify_check = verify_conn.execute("PRAGMA integrity_check;").fetchone()[0]
        if verify_check != "ok":
            if backup_path.exists():
                backup_path.unlink()
            raise ValueError(f"Backup file failed integrity verification: {verify_check}")
    finally:
        verify_conn.close()

    size_bytes = backup_path.stat().st_size

    # 4. Rotate older backups (keep last N)
    rotate_old_backups(keep_count=MAX_BACKUP_RETENTION)

    logger.info(f"Database backup created: {backup_filename} ({size_bytes} bytes)")
    return {
        "success": True,
        "filename": backup_filename,
        "path": str(backup_path),
        "size_bytes": size_bytes,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "integrity": "verified"
    }

def list_database_backups() -> List[Dict[str, Any]]:
    """List available database backups with metadata."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = []
    
    for file_path in sorted(BACKUP_DIR.glob("spendsense_backup_*.db"), reverse=True):
        stat = file_path.stat()
        dt_str = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.timezone.utc).isoformat()
        backups.append({
            "filename": file_path.name,
            "size_bytes": stat.st_size,
            "size_human": format_size(stat.st_size),
            "created_at": dt_str
        })
    return backups

def restore_database_backup(backup_filename: str) -> Dict[str, Any]:
    """
    Safely restore database from a verified backup file.
    Creates an automatic pre-restore backup first.
    """
    # Prevent directory traversal
    clean_name = Path(backup_filename).name
    backup_path = BACKUP_DIR / clean_name

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file '{clean_name}' not found.")

    # 1. Verify backup file integrity
    b_conn = sqlite3.connect(backup_path)
    try:
        b_check = b_conn.execute("PRAGMA integrity_check;").fetchone()[0]
        if b_check != "ok":
            raise ValueError(f"Backup file failed integrity check: {b_check}")
    finally:
        b_conn.close()

    # 2. Take emergency pre-restore snapshot of current live database
    prerestore_name = None
    if DB_PATH.exists():
        try:
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
            prerestore_name = f"spendsense_prerestore_{timestamp}.db"
            pre_path = BACKUP_DIR / prerestore_name
            with sqlite3.connect(DB_PATH) as cur_conn:
                with sqlite3.connect(pre_path) as pre_conn:
                    cur_conn.backup(pre_conn)
        except Exception as e:
            logger.warning(f"Failed to create pre-restore snapshot: {e}")

    # 3. Restore from backup
    with sqlite3.connect(backup_path) as src_conn:
        with sqlite3.connect(DB_PATH) as target_conn:
            src_conn.backup(target_conn)

    # 4. Verify target live DB
    with sqlite3.connect(DB_PATH) as live_conn:
        live_check = live_conn.execute("PRAGMA integrity_check;").fetchone()[0]
        if live_check != "ok":
            raise ValueError(f"Restored database failed integrity check: {live_check}")

    logger.info(f"Database successfully restored from {clean_name}")
    return {
        "success": True,
        "message": f"Database successfully restored from {clean_name}",
        "restored_from": clean_name,
        "prerestore_snapshot": prerestore_name,
        "integrity": "verified",
        "restored_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

def rotate_old_backups(keep_count: int = 10) -> None:
    """Retain only the latest N backup files and delete older ones."""
    backup_files = sorted(BACKUP_DIR.glob("spendsense_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(backup_files) > keep_count:
        for old_file in backup_files[keep_count:]:
            try:
                old_file.unlink()
                logger.info(f"Deleted rotated old backup: {old_file.name}")
            except Exception as e:
                logger.warning(f"Error removing old backup {old_file}: {e}")

def format_size(bytes_num: int) -> str:
    """Format bytes into readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} TB"
