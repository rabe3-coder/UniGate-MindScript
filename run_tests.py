"""Run isolated standard-library regression tests without touching project user data."""
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SUITE=(
    'test_concurrency.py',
    'test_layered_workflows.py',
    'test_student_management.py',
    'test_academics.py',
    'test_http_new_features.py',
)

if __name__=='__main__':
    for script in SUITE:
        print('\n===',script,'===',flush=True)
        result=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,check=False,env={**os.environ, 'MINDSCRIPT_TEST_DEMO':'1'})
        if result.returncode!=0:
            raise SystemExit(result.returncode)
    result=subprocess.run([sys.executable,str(ROOT/'test_accounts.py')],cwd=ROOT,check=False,env={**os.environ, 'MINDSCRIPT_TEST_DEMO':'0'})
    if result.returncode!=0:raise SystemExit(result.returncode)
    print('\nPASS: all isolated checks completed.')
