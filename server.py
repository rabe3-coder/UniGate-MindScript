#!/usr/bin/env python3
"""Backward-compatible startup entrypoint for the layered eng.rabe3 application.

Run `python server.py`. The code now lives in `app/` rather than in this file.
"""
from http.server import ThreadingHTTPServer
from app.core import config
from app.domain.errors import AppError
from app.infrastructure import database as db
from app.services.registration import enroll_basket
from app.http.handler import Handler

# Compatibility for the original concurrency test that reassigns server.DB_PATH.
DB_PATH=config.DB_PATH

def init_db():
    config.DB_PATH=DB_PATH
    return db.init_db()

def connect(path=None):
    return db.connect(path)

one=db.one

def main():
    init_db()
    server=ThreadingHTTPServer((config.HOST,config.PORT),Handler)
    print(f'Mind Script eng.rabe3 — http://{config.HOST}:{config.PORT}')
    print('Local demonstration only — Press Ctrl+C to stop')
    try:server.serve_forever()
    except KeyboardInterrupt:print('\nServer stopped.')
    finally:server.server_close()

if __name__=='__main__': main()
