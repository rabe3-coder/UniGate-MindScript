"""Labs application operations (one function per endpoint)."""
from app.core.security import require
from app.services.scenarios import sandbox

def op_lab_run(c, user, payload, respond, headers, request_path, method, path):
    require(user)
    case = int(payload.get('case', 0))
    return respond(sandbox(case))

