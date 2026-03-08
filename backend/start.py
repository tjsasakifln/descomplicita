"""Startup script with crash diagnostics for Railway deployment."""
import sys
import os

print(f"[boot] Python {sys.version}", flush=True)
print(f"[boot] PORT={os.environ.get('PORT', 'NOT SET')}", flush=True)
print(f"[boot] CWD={os.getcwd()}", flush=True)

try:
    import uvicorn
    print(f"[boot] uvicorn {uvicorn.__version__} OK", flush=True)

    from main import app
    print("[boot] main:app imported OK", flush=True)

    port = int(os.environ.get("PORT", "8000"))
    print(f"[boot] Starting on 0.0.0.0:{port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
except Exception as e:
    print(f"[boot] FATAL: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
