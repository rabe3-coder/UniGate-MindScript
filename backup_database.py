#!/usr/bin/env python3
"""Private, consistent backups/restores for the UniGate SQLite database.

Only run restore while web workers and local server are STOPPED.
Do not commit or publicly upload backups; they contain account records.
"""
import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from app.core.config import DB_PATH


def backup(target):
    target = Path(target).expanduser().resolve()
    source = DB_PATH.resolve()
    if target == source: raise SystemExit('Refusing to overwrite the live database.')
    if not source.is_file(): raise SystemExit('Database not found: ' + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): raise SystemExit('Refusing to overwrite an existing backup.')
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as incoming, sqlite3.connect(target) as outgoing:
        incoming.backup(outgoing)
        status = outgoing.execute('PRAGMA integrity_check').fetchone()[0]
        if status != 'ok': raise SystemExit('Backup integrity check failed: ' + status)
    if os.name != 'nt': target.chmod(0o600)
    print(f'Backup created: {target} ({target.stat().st_size} bytes)')
    print('PRIVATE DATA: store offline/encrypted, never upload to public GitHub.')


def restore(source, confirmation):
    if confirmation != 'RESTORE_PRIVATE_BACKUP':
        raise SystemExit('Restoring overwrites the live database. Specify --confirm RESTORE_PRIVATE_BACKUP.')
    source = Path(source).expanduser().resolve()
    target = DB_PATH.resolve()
    if source == target or not source.is_file(): raise SystemExit('Invalid backup file.')
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise SystemExit('Backup damaged. No changes made.')
    if target.exists():
        raise SystemExit('Refusing to overwrite existing live database. Move it out of the way AFTER stopping the app and saving a separate copy.')
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as incoming, sqlite3.connect(target) as outgoing:
        incoming.backup(outgoing)
    if os.name != 'nt': target.chmod(0o600)
    print('Backup restored to', target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('operation', choices=('backup', 'restore'))
    ap.add_argument('--file', help='Backup file path. Restore requires --file')
    ap.add_argument('--confirm', default='')
    args = ap.parse_args()
    if args.operation == 'backup':
        name = args.file or str(DB_PATH.parent / 'backups' / ('unigate_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S') + '.sqlite3'))
        backup(name)
    else:
        if not args.file: ap.error('restore requires --file')
        restore(args.file, args.confirm)


if __name__ == '__main__': main()
