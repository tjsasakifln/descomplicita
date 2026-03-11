"""Startup script with crash diagnostics for Railway deployment."""

import os
import sys


# Print to BOTH stdout and stderr to ensure Railway captures output
def log(msg):
    print(msg, flush=True)
    print(msg, file=sys.stderr, flush=True)


log(f"[boot] Python {sys.version}")
log(f"[boot] PORT={os.environ.get('PORT', 'NOT SET')}")
log(f"[boot] CWD={os.getcwd()}")
log(f"[boot] PYTHONPATH={os.environ.get('PYTHONPATH', 'NOT SET')}")

try:
    log("[boot] importing uvicorn...")
    import uvicorn

    log(f"[boot] uvicorn {uvicorn.__version__} OK")

    log("[boot] importing main:app...")
    from main import app

    log("[boot] main:app imported OK")

    port = int(os.environ.get("PORT", "8000"))
    log(f"[boot] Starting uvicorn on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
except Exception as e:
    log(f"[boot] FATAL: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
    traceback.print_exc(file=sys.stdout)
    sys.exit(1)
