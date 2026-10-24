#!/usr/bin/env python3
"""Local-only provisioning of the sole administrator and exactly three affairs logins.

No HTTP endpoint permits assigning a privileged role. Secrets are typed with getpass,
hashed with PBKDF2-HMAC-SHA256, and are not printed or written to code/config files.
"""
import argparse
import getpass
import re
import sys
from dataclasses import dataclass
from app.core.crypto import password_hash
from app.infrastructure.database import init_db, connect, one, transaction, audit

USERNAME = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{2,31}\Z')

@dataclass
class Staff:
    slot: str
    role: str
    username: str
    name: str
    password: str

def _name(prompt):
    while True:
        value=input(prompt).strip()
        if 3 <= len(value) <= 100 and all(ord(ch)>=32 for ch in value):
            return value
        print('Please enter a full display name (3-100 chars).')

def _username(prompt):
    while True:
        value=input(prompt).strip()
        if USERNAME.fullmatch(value):return value
        print('Use 3-32 characters: start with a Latin letter; letters/digits/._- are allowed.')

def _password():
    while True:
        value=getpass.getpass('Password (12+ chars; letters, digits and a symbol): ')
        if len(value)<12 or len(value)>128 or not any(x.isalpha() for x in value) or not any(x.isdigit() for x in value) or not any(not x.isalnum() for x in value):
            print('Choose a stronger password: 12+ characters with letters, numbers and a symbol.')
            continue
        confirm=getpass.getpass('Confirm password: ')
        if confirm!=value:
            print('Passwords do not match. Try again.')
            continue
        return value

def collect(slot,role,label):
    print(f'\n--- {label} ({slot}) ---')
    username=_username('Login username: ')
    name=_name('Display name: ')
    password=_password()
    return Staff(slot,role,username,name,password)

def provision(staff, selected_roles):
    """Atomic update: preserve old staff user IDs and their audit rows where possible."""
    init_db()
    c=connect()
    try:
        with transaction(c):
            if len({x.slot for x in staff})!=len(staff) or len({x.username.casefold() for x in staff})!=len(staff):
                raise ValueError('Duplicate staff slots or login names.')
            if any(one(c, '''SELECT 1 FROM users WHERE role='student'
                       AND (username=? COLLATE NOCASE OR student_number=? COLLATE NOCASE)''',
                       (x.username,x.username)) for x in staff):
                raise ValueError('Staff login conflicts with an existing student account.')
            # Inactive legacy accounts cannot retain leaked demo credentials.
            c.execute('UPDATE users SET is_active=0 WHERE role IN (%s)' % ','.join('?'*len(selected_roles)),tuple(selected_roles))
            c.execute('DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE role IN (%s))' % ','.join('?'*len(selected_roles)),tuple(selected_roles))
            claimed=set()
            for item in staff:
                row=one(c,'SELECT id FROM users WHERE staff_slot=?',(item.slot,))
                if not row:
                    # Reuse a historic account when possible: references remain intact.
                    options=c.execute('''SELECT id FROM users WHERE role=? AND staff_slot IS NULL
                                         ORDER BY id''',(item.role,)).fetchall()
                    row=next((r for r in options if r['id'] not in claimed),None)
                if row:
                    uid=row['id']
                    claimed.add(uid)
                    conflict=one(c,'SELECT id FROM users WHERE username=? COLLATE NOCASE AND id<>?',(item.username,uid))
                    if conflict:
                        raise ValueError(f'Login already in use: {item.username}')
                    c.execute('''UPDATE users SET username=?,name_ar=?,name_en=?,role=?,password_hash=?,
                       is_active=1,staff_slot=? WHERE id=?''',
                       (item.username,item.name,item.name,item.role,password_hash(item.password),item.slot,uid))
                else:
                    if one(c,'SELECT 1 FROM users WHERE username=? COLLATE NOCASE',(item.username,)):
                        raise ValueError(f'Login already in use: {item.username}')
                    uid=c.execute('''INSERT INTO users(username,name_ar,name_en,role,password_hash,is_active,staff_slot)
                        VALUES(?,?,?,?,?,1,?)''',(item.username,item.name,item.name,item.role,password_hash(item.password),item.slot)).lastrowid
                audit(c,None,'STAFF_PROVISIONED','users',{'staff_slot':item.slot,'staff_id':uid,'role':item.role})
    finally:c.close()

def main():
    parser=argparse.ArgumentParser(description='Assign private administrator and staff credentials (local console only).')
    parser.add_argument('command',nargs='?',choices=('setup','set-role'),default='setup')
    parser.add_argument('--role',choices=('head','finance'),help='Only for set-role')
    args=parser.parse_args()
    if args.command=='setup':
        print('Configure exactly one ADMIN and three STUDENT AFFAIRS officers.')
        print('Passwords are hidden and only their salted hashes are stored in SQLite.')
        data=[collect('ADMIN','admin','System administrator')]
        for i in range(1,4):data.append(collect(f'AFFAIRS_{i}','affairs',f'Student affairs officer {i}'))
        print('\nThe configured account names will be:')
        for item in data: print(f'  {item.slot}: {item.username}')
        if input('Type CONFIRM to save these credentials: ').strip()!='CONFIRM':
            print('Cancelled; no database updates.');return 1
        provision(data,('admin','affairs'))
        print('Saved: one admin and three affairs users. Old staff sessions invalidated.')
    else:
        if not args.role:parser.error('--role is required with set-role')
        data=[collect(args.role.upper(),args.role,args.role.title()+' staff login')]
        if input('Type CONFIRM to save: ').strip()!='CONFIRM':return 1
        provision(data,(args.role,))
        print(f'Saved {args.role} credentials.')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyboardInterrupt) as error:
        print('\nERROR: '+str(error),file=sys.stderr)
        sys.exit(1)
