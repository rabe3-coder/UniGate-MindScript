"""Runtime configuration, resolved relative to project root."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get('MINDSCRIPT_DB', str(ROOT / 'registration.sqlite3')))
# Keep the Windows default, but accept host/port injected by hosting providers.
HOST = os.environ.get('MINDSCRIPT_HOST', '0.0.0.0' if os.environ.get('PORT') else '127.0.0.1')
PORT = int(os.environ.get('PORT') or os.environ.get('MINDSCRIPT_PORT', '8765'))
PUBLIC_ORIGIN = os.environ.get('UNIGATE_PUBLIC_ORIGIN', '').rstrip('/')
# Legacy seed credentials are used only by isolated regression tests.
DEMO_PASSWORD = 'Demo123!'
