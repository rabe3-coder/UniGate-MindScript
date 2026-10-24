#!/usr/bin/env python3
"""Local maintenance tool to rotate a student password without changing their records."""
import getpass
import sys
from app.core.crypto import password_hash
from app.infrastructure.database import init_db,connect,one,transaction,audit

def main():
    init_db()
    identifier=input('University number or student username: ').strip()
    c=connect()
    try:
        student=one(c,"SELECT id,username,name_ar FROM users WHERE role='student' AND (username=? OR student_number=?)",(identifier,identifier))
        if not student:raise ValueError('Student not found')
        print('Student:',student['name_ar'],' / ',student['username'])
        pwd=getpass.getpass('New password (10+ chars with letters and digits): ')
        if len(pwd)<10 or len(pwd)>128 or not any(x.isalpha() for x in pwd) or not any(x.isdigit() for x in pwd):
            raise ValueError('Weak password')
        if getpass.getpass('Confirm new password: ')!=pwd:
            raise ValueError('Passwords do not match')
        with transaction(c):
            c.execute('UPDATE users SET password_hash=?,is_active=1 WHERE id=?',(password_hash(pwd),student['id']))
            c.execute('DELETE FROM sessions WHERE user_id=?',(student['id'],))
            audit(c,None,'STUDENT_PASSWORD_ROTATED','student',{'student_id':student['id']})
        print('Password updated; old student sessions invalidated.')
    finally:c.close()

if __name__=='__main__':
    try:main()
    except (KeyboardInterrupt,ValueError) as e:
        print('\nERROR:',e,file=sys.stderr)
        sys.exit(1)
