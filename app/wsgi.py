"""WSGI transport for zero-cost PythonAnywhere deployment.

No change to application use cases, data access or frontend is needed.
For local Windows use `python server.py` as before.
"""
import json
import mimetypes
import os
import sqlite3
import sys
from http import HTTPStatus
from pathlib import Path
from urllib.parse import unquote, urlsplit
from app.core import config
from app.core.security import user_from_cookie, require
from app.domain.errors import AppError
from app.infrastructure.database import init_db, connect, audit
from app.api.router import dispatch
from app.http.handler import Response, allow_auth_attempt

# Do not accidentally enable destructive sandbox reset or demo credentials online.
if config.PUBLIC_ORIGIN and os.environ.get('MINDSCRIPT_TEST_DEMO') == '1':
    raise RuntimeError('MINDSCRIPT_TEST_DEMO must never be enabled on a public deployment')

# Called once per worker startup, never deletes existing accounts or registrations.
init_db()

_BASE = (config.ROOT / 'static').resolve()
_SECURITY_HEADERS = [
    ('X-Content-Type-Options', 'nosniff'),
    ('X-Frame-Options', 'DENY'),
    ('Referrer-Policy', 'no-referrer'),
]

def _respond(start_response, status, body, content_type='application/json; charset=utf-8', cookie=None, cache='no-store'):
    if isinstance(body, str): body = body.encode('utf-8')
    headers = [('Content-Type', content_type), ('Content-Length', str(len(body))), ('Cache-Control', cache)] + _SECURITY_HEADERS
    if cookie: headers.append(('Set-Cookie', cookie))
    start_response(f'{status} {HTTPStatus(status).phrase}', headers)
    return [body]

def _json(start_response, status, data, cookie=None):
    return _respond(start_response, status, json.dumps(data, ensure_ascii=False, default=str), cookie=cookie)

def _headers(environ):
    headers = {}
    for key, value in environ.items():
        if key.startswith('HTTP_'):
            name = '-'.join(segment.capitalize() for segment in key[5:].split('_'))
            headers[name] = value
    headers['Content-Type'] = environ.get('CONTENT_TYPE', '')
    headers['Content-Length'] = environ.get('CONTENT_LENGTH', '')
    return headers

def _payload(environ):
    try: size = int(environ.get('CONTENT_LENGTH') or '0')
    except (TypeError, ValueError): raise AppError('Invalid content length', 400)
    if size < 0 or size > 100_000: raise AppError('Request too large', 413)
    if size and 'application/json' not in environ.get('CONTENT_TYPE', ''):
        raise AppError('JSON body required', 415)
    try: data = json.loads(environ['wsgi.input'].read(size) or b'{}')
    except (ValueError, UnicodeDecodeError): raise AppError('Invalid JSON', 400)
    if not isinstance(data, dict): raise AppError('Object body required', 400)
    return data

def _same_origin(environ, headers):
    # A public HTTPS deployment must reject missing or mismatched Origin on mutations.
    fetch_site = headers.get('Sec-Fetch-Site', '')
    if fetch_site == 'cross-site': return False
    origin = headers.get('Origin', '')
    if config.PUBLIC_ORIGIN:
        return origin == config.PUBLIC_ORIGIN and fetch_site != 'cross-site'
    # Local WSGI regression tests retain the original local client behavior.
    return not origin or origin in (f'http://127.0.0.1:{config.PORT}', f'http://localhost:{config.PORT}')

def _application(environ, start_response):
    method = (environ.get('REQUEST_METHOD') or 'GET').upper()
    path = unquote(environ.get('PATH_INFO') or '/')
    if path == '/healthz':
        return _json(start_response, 200, {'status':'ok'})
    if path.startswith('/api/'):
        if method not in ('GET', 'POST'):
            return _json(start_response, 405, {'error':'Method not allowed'})
        headers = _headers(environ)
        if method == 'POST' and not _same_origin(environ, headers):
            return _json(start_response, 403, {'error':'Request origin not allowed', 'code':'ORIGIN'})
        if method == 'POST' and path in ('/api/login', '/api/signup'):
            # WSGI gateway REMOTE_ADDR must be used, not user-supplied X-Forwarded-For.
            if not allow_auth_attempt(environ.get('REMOTE_ADDR') or 'unknown'):
                return _json(start_response, 429, {'error':'Too many attempts', 'code':'RATE_LIMIT'})
        try:
            c = connect()
        except sqlite3.Error as error:
            print('Database connection unavailable:', type(error).__name__, file=sys.stderr)
            return _json(start_response, 503, {'error':'Service temporarily unavailable','code':'DATABASE_UNAVAILABLE'})
        user = None
        try:
            user = user_from_cookie(c, headers.get('Cookie', ''))
            if path not in ('/api/login', '/api/signup', '/api/logout'): require(user)
            url = path + (('?' + environ['QUERY_STRING']) if environ.get('QUERY_STRING') else '')
            result = dispatch(method, path, c, user, lambda:_payload(environ), Response, headers, url)
            if result is None: raise AppError('API route not found',404,'NOT_FOUND')
            return _json(start_response, result.status, result.data, result.cookie)
        except AppError as error:
            if user and method=='POST' and path in ('/api/register', '/api/drop','/api/waitlist/join','/api/waitlist/leave','/api/payment/request','/api/section/capacity'):
                try: audit(c, user['id'], 'REJECTED_REQUEST', path, {'code':error.code, 'reason':str(error)})
                except sqlite3.Error: pass
            return _json(start_response, error.status, {'error':str(error), 'code':error.code})
        except sqlite3.IntegrityError:
            return _json(start_response, 409, {'error':'Constraint violated','code':'CONSTRAINT'})
        except (TypeError, ValueError):
            return _json(start_response, 400, {'error':'Invalid fields','code':'VALIDATION'})
        except sqlite3.OperationalError as error:
            print('Database unavailable:', type(error).__name__, file=sys.stderr)
            return _json(start_response, 503, {'error':'Service temporarily unavailable','code':'DATABASE_UNAVAILABLE'})
        except Exception as error:
            print('Unhandled request error:', type(error).__name__, file=sys.stderr)
            return _json(start_response, 500, {'error':'Unexpected server error','code':'SERVER'})
        finally: c.close()
    if method != 'GET':
        return _json(start_response, 404, {'error':'Not found'})
    rel = path.lstrip('/') or 'index.html'
    file = (_BASE / rel).resolve()
    if _BASE not in file.parents or not file.is_file():
        return _json(start_response, 404, {'error':'Not found'})
    try: body=file.read_bytes()
    except OSError:
        return _json(start_response, 503, {'error':'Asset unavailable'})
    content_type=mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
    if content_type.startswith('text/') or 'javascript' in content_type:
        content_type += '; charset=utf-8'
    return _respond(start_response, 200, body, content_type, cache='public, max-age=300')

def application(environ, start_response):
    if config.PUBLIC_ORIGIN.startswith('https://') and environ.get('wsgi.url_scheme') == 'http':
        location=config.PUBLIC_ORIGIN + (environ.get('PATH_INFO') or '/')
        if environ.get('QUERY_STRING'): location += '?' + environ['QUERY_STRING']
        start_response('308 Permanent Redirect', [('Location', location), ('Content-Length','0')])
        return [b'']
    return _application(environ,start_response)
