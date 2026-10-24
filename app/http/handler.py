"""HTTP transport layer: validate JSON and headers, send responses, serve static assets."""
import json
import mimetypes
import os
import sqlite3
import time
import threading
import sys
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from app.core.config import ROOT, PORT, PUBLIC_ORIGIN
from app.core.security import user_from_cookie, require
from app.domain.errors import AppError
from app.infrastructure.database import connect, audit
from app.api.router import dispatch

_AUTH_LOCK=threading.Lock()
_AUTH_ATTEMPTS={}

def allow_auth_attempt(ip):
    """Best-effort local per-process limit; reverse proxies need their own limiter."""
    now=time.monotonic()
    with _AUTH_LOCK:
        times=[v for v in _AUTH_ATTEMPTS.get(ip,[]) if now-v<60]
        if len(times)>=20: return False
        times.append(now)
        _AUTH_ATTEMPTS[ip]=times
        if len(_AUTH_ATTEMPTS)>500:
            for key in list(_AUTH_ATTEMPTS)[:100]:_AUTH_ATTEMPTS.pop(key,None)
        return True

@dataclass(frozen=True)
class Response:
    data: object
    status: int = 200
    cookie: str | None = None

class Handler(BaseHTTPRequestHandler):
    server_version = 'MindScriptLayered/2.0'

    def log_message(self, fmt, *args):
        if os.environ.get('MINDSCRIPT_QUIET') != '1':
            super().log_message(fmt, *args)

    def send_json(self, data, status=200, cookie=None):
        encoded = json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(status)
        for name,value in {
            'Content-Type': 'application/json; charset=utf-8',
            'Cache-Control': 'no-store',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'Referrer-Policy': 'no-referrer',
            'Content-Length': str(len(encoded)),
        }.items(): self.send_header(name,value)
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers()
        self.wfile.write(encoded)

    def body(self):
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:raise AppError('Invalid content length',400)
        if size<0 or size>100_000: raise AppError('Request too large',413)
        if size and 'application/json' not in self.headers.get('Content-Type',''):
            raise AppError('JSON body required',415)
        try:
            payload=json.loads(self.rfile.read(size) or '{}')
        except (ValueError,UnicodeDecodeError):
            raise AppError('Invalid JSON',400)
        if not isinstance(payload,dict):raise AppError('Object body required',400)
        return payload

    def _api(self, method, path):
        # Same-origin guard for authenticated POST operations; JSON is required.
        if method=='POST':
            if self.headers.get('Sec-Fetch-Site')=='cross-site':
                return self.send_json({'error':'Cross-site requests are not allowed','code':'ORIGIN'},403)
            origin=self.headers.get('Origin','')
            accepted = {PUBLIC_ORIGIN} if PUBLIC_ORIGIN else {f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'}
            if origin and origin not in accepted:
                return self.send_json({'error':'Cross-site requests are not allowed','code':'ORIGIN'},403)
        if method=='POST' and path in ('/api/signup','/api/login') and not allow_auth_attempt(self.client_address[0]):
            return self.send_json({'error':'Too many attempts; retry later / محاولات كثيرة، أعد المحاولة لاحقاً','code':'RATE_LIMIT'},429)
        c=connect()
        user=None
        try:
            user=user_from_cookie(c,self.headers.get('Cookie',''))
            if path not in ('/api/login','/api/signup','/api/logout'): require(user)
            response=dispatch(method,path,c,user,self.body,Response,self.headers,self.path)
            if response is None:raise AppError('API route not found',404,'NOT_FOUND')
            self.send_json(response.data,response.status,response.cookie)
        except AppError as error:
            if user and method=='POST' and path in {
                '/api/register','/api/drop','/api/waitlist/join','/api/waitlist/leave',
                '/api/payment/request','/api/section/capacity'}:
                try:
                    audit(c,user['id'],'REJECTED_REQUEST',path,{'code':error.code,'reason':str(error)})
                except sqlite3.Error:pass
            self.send_json({'error':str(error),'code':error.code},error.status)
        except sqlite3.IntegrityError:
            self.send_json({'error':'Constraint violated / مخالفة قيد البيانات','code':'CONSTRAINT'},409)
        except (TypeError,ValueError):
            self.send_json({'error':'Invalid fields / حقول غير صالحة','code':'VALIDATION'},400)
        except Exception as error:
            print('INTERNAL ERROR:',repr(error),file=sys.stderr)
            self.send_json({'error':'Unexpected server error / خطأ داخلي في الخادم','code':'SERVER'},500)
        finally:
            c.close()

    def handle_request(self,method):
        path=urlparse(self.path).path
        if path == '/healthz':
            return self.send_json({'status':'ok'})
        if path.startswith('/api/'):
            return self._api(method,path)
        if method!='GET':return self.send_json({'error':'Not found'},404)
        rel=path.lstrip('/') or 'index.html'
        base=(ROOT/'static').resolve()
        file=(base/rel).resolve()
        if base not in file.parents or not file.is_file():
            self.send_error(404);return
        content=file.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',(mimetypes.guess_type(str(file))[0] or 'application/octet-stream')+'; charset=utf-8')
        self.send_header('Content-Length',str(len(content)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-cache')
        self.end_headers();self.wfile.write(content)

    def do_GET(self):self.handle_request('GET')
    def do_POST(self):self.handle_request('POST')
