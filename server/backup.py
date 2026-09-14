#!/usr/bin/env python3
"""Consistent SQLite backup with retention; intended for systemd timer on the VPS."""
from pathlib import Path
from datetime import datetime, timezone
import os, sqlite3, time

DB=Path(os.environ.get("WEDDING_DB_PATH","/var/lib/boda-julian-carla/wedding.sqlite3"))
DEST=Path(os.environ.get("WEDDING_BACKUP_DIR","/var/backups/boda-julian-carla"))
KEEP_DAYS=int(os.environ.get("WEDDING_BACKUP_KEEP_DAYS","45"))

def main():
    if not DB.exists(): raise SystemExit(f"No existe la base: {DB}")
    DEST.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tmp=DEST/f".wedding-{stamp}.sqlite3.tmp"
    final=DEST/f"wedding-{stamp}.sqlite3"
    src=sqlite3.connect(f"file:{DB}?mode=ro",uri=True,timeout=10)
    dst=sqlite3.connect(tmp)
    try: src.backup(dst)
    finally: dst.close(); src.close()
    tmp.replace(final)
    cutoff=time.time()-KEEP_DAYS*86400
    for f in DEST.glob("wedding-*.sqlite3"):
        if f.stat().st_mtime<cutoff: f.unlink(missing_ok=True)
    print(final)

if __name__=="__main__": main()
