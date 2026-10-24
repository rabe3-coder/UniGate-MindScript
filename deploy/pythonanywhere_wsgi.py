"""Paste/adapt this into the WSGI config file on PythonAnywhere > Web tab.
Replace YOUR_PYTHONANYWHERE_USERNAME before using it.
The SQLite file lives in private persistent home storage OUTSIDE the git checkout.
"""
import os
import sys
from pathlib import Path

USER = 'YOUR_PYTHONANYWHERE_USERNAME'  # Change to your username.
PROJECT = Path('/home') / USER / 'unigate'
DATA = Path('/home') / USER / 'unigate_data'
DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
os.environ['MINDSCRIPT_DB'] = str(DATA / 'registration.sqlite3')
os.environ['UNIGATE_PUBLIC_ORIGIN'] = f'https://{USER}.pythonanywhere.com'
os.environ['UNIGATE_SQLITE_JOURNAL'] = 'DELETE'
os.environ.pop('MINDSCRIPT_TEST_DEMO', None)
from app.wsgi import application
