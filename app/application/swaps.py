"""Swaps application operations (one function per endpoint)."""
from app.services.swaps import swap_overview, request_swap, cancel_swap

def op_swap(c, user, payload, respond, headers, request_path, method, path):
    return respond(swap_overview(c, user))


def op_swap_request(c, user, payload, respond, headers, request_path, method, path):
    return respond(request_swap(c, user, payload.get('from_section_id'), payload.get('to_section_id')), 201)


def op_swap_cancel(c, user, payload, respond, headers, request_path, method, path):
    return respond(cancel_swap(c, user, payload.get('request_id')))

