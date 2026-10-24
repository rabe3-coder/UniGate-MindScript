"""Payments application operations (one function per endpoint)."""
from app.domain.errors import AppError
from app.core.clock import now
from app.core.security import require
from app.infrastructure.database import one, transaction, audit
import secrets

def op_payment_request(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['student'])
    body = payload
    key = body.get('request_key')
    outcome = body.get('outcome', 'pending')
    if outcome not in ['pending', 'success', 'failed'] or not isinstance(key, str) or (not 8 <= len(key) <= 100):
        raise AppError('Invalid demo payment request')
    with transaction(c):
        old = one(c, 'SELECT * FROM payments WHERE user_id=? AND request_key=?', (user['id'], key))
        if old:
            row = dict(old)
            row['replayed'] = True
        else:
            state = {'pending': 'pending', 'success': 'confirmed', 'failed': 'failed'}[outcome]
            ref = 'SIM-' + secrets.token_hex(5).upper()
            c.execute('INSERT INTO payments(user_id,request_key,reference,status,gateway_status,created_at) VALUES(?,?,?,?,?,?)', (user['id'], key, ref, state, outcome, now()))
            row = dict(one(c, 'SELECT * FROM payments WHERE reference=?', (ref,)))
            audit(c, user['id'], 'PAYMENT_DEMO', 'payment', {'reference': ref, 'status': state, 'no_real_charge': True})
    return respond({'payment': row, 'simulated': True})


def op_payment_reconcile(c, user, payload, respond, headers, request_path, method, path):
    require(user, ['finance', 'admin'])
    body = payload
    pid = int(body.get('payment_id', 0))
    outcome = body.get('status')
    if outcome not in ['confirmed', 'failed']:
        raise AppError('Invalid verification result')
    with transaction(c):
        p = one(c, 'SELECT * FROM payments WHERE id=?', (pid,))
        if not p:
            raise AppError('Payment not found', 404)
        if p['status'] != 'pending':
            raise AppError('Only pending payments can be reconciled', 409)
        c.execute('UPDATE payments SET status=?,gateway_status=? WHERE id=?', (outcome, 'success' if outcome == 'confirmed' else 'failed', pid))
        audit(c, user['id'], 'PAYMENT_RECONCILE', 'payment', {'payment_id': pid, 'status': outcome, 'simulated': True})
    return respond({'success': True})

