#!/usr/bin/env python3
"""Load test script for BidIQ search pipeline (SP-001.5)."""

import argparse
import requests
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def poll_job(base_url: str, job_id: str, timeout: int = 300) -> dict:
    """Poll /status/<job_id> until done or timeout. Returns result dict."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = requests.get(f"{base_url}/status/{job_id}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "")
            if status in ("completed", "failed", "error"):
                return data
        except requests.RequestException as exc:
            return {"status": "error", "error": str(exc)}
        time.sleep(2)
    return {"status": "error", "error": f"Timed out after {timeout}s"}


def start_search(base_url: str, ufs: list[str], days: int) -> tuple[str | None, str | None]:
    """POST /buscar and return (job_id, error)."""
    today = date.today()
    payload = {
        "ufs": ufs,
        "data_inicio": (today - timedelta(days=days)).isoformat(),
        "data_fim": today.isoformat(),
    }
    try:
        resp = requests.post(f"{base_url}/buscar", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        job_id = data.get("job_id") or data.get("id")
        if not job_id:
            return None, f"No job_id in response: {data}"
        return job_id, None
    except requests.RequestException as exc:
        return None, str(exc)


def run_search(base_url: str, ufs: list[str], days: int, poll_timeout: int = 300) -> tuple[float, str]:
    """Run a full search (POST + poll). Returns (elapsed_seconds, status_str)."""
    t0 = time.monotonic()
    job_id, err = start_search(base_url, ufs, days)
    if err:
        return time.monotonic() - t0, f"ERROR: {err}"
    result = poll_job(base_url, job_id, timeout=poll_timeout)
    elapsed = time.monotonic() - t0
    if result.get("status") in ("completed",):
        return elapsed, "ok"
    return elapsed, f"ERROR: {result.get('error', result.get('status', 'unknown'))}"


# ---------------------------------------------------------------------------
# Table printer
# ---------------------------------------------------------------------------

def _row(col1: str, col2: str, col3: str, widths: tuple[int, int, int]) -> str:
    return f"| {col1:<{widths[0]}} | {col2:<{widths[1]}} | {col3:<{widths[2]}} |"


def _sep(widths: tuple[int, int, int]) -> str:
    return f"|{'-' * (widths[0] + 2)}|{'-' * (widths[1] + 2)}|{'-' * (widths[2] + 2)}|"


def print_table(title: str, headers: tuple[str, str, str], rows: list[tuple[str, str, str]]) -> None:
    w0 = max(len(headers[0]), *(len(r[0]) for r in rows))
    w1 = max(len(headers[1]), *(len(r[1]) for r in rows))
    w2 = max(len(headers[2]), *(len(r[2]) for r in rows))
    widths = (w0, w1, w2)
    print(f"\n--- {title} ---")
    print(_row(*headers, widths))
    print(_sep(widths))
    for r in rows:
        print(_row(*r, widths))


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_latency(base_url: str) -> list[tuple[str, str, str]]:
    """Run latency tests and return table rows."""
    cases = [
        ("1 UF + 7 days",   ["SP"], 7),
        ("5 UFs + 7 days",  ["SP", "RJ", "MG", "RS", "BA"], 7),
        ("3 UFs + 30 days", ["SP", "RJ", "MG"], 30),
    ]
    rows: list[tuple[str, str, str]] = []
    for label, ufs, days in cases:
        print(f"  Running: {label} ...", flush=True)
        elapsed, status = run_search(base_url, ufs, days)
        if status == "ok":
            verdict = "PASS"
        else:
            verdict = f"FAIL ({status})"
        rows.append((label, f"{elapsed:.1f}", verdict))
    return rows


def scenario_cache(base_url: str) -> list[tuple[str, str, str]]:
    """Run cache tests and return table rows."""
    ufs = ["SP"]
    days = 7
    rows: list[tuple[str, str, str]] = []

    print("  Running: First search (cache warm-up) ...", flush=True)
    t1, s1 = run_search(base_url, ufs, days)
    v1 = "baseline" if s1 == "ok" else f"FAIL ({s1})"
    rows.append(("First search", f"{t1:.1f}", v1))

    print("  Running: Second search (cache) ...", flush=True)
    t2, s2 = run_search(base_url, ufs, days)
    if s2 == "ok":
        v2 = "PASS (<5s)" if t2 < 5 else f"SLOW ({t2:.1f}s)"
    else:
        v2 = f"FAIL ({s2})"
    rows.append(("Second search (cache)", f"{t2:.1f}", v2))

    # Cache stats
    print("  Fetching: /cache/stats ...", flush=True)
    try:
        resp = requests.get(f"{base_url}/cache/stats", timeout=10)
        resp.raise_for_status()
        stats = resp.json()
        hit_ratio = stats.get("hit_ratio", stats.get("hits_ratio", None))
        if hit_ratio is not None:
            ratio_val = float(hit_ratio)
            verdict = "PASS (>90%)" if ratio_val >= 0.90 else f"LOW ({ratio_val:.2f})"
            rows.append(("Cache hit ratio", f"{ratio_val:.2f}", verdict))
        else:
            rows.append(("Cache hit ratio", "N/A", f"WARN (key not found: {list(stats.keys())})"))
    except requests.RequestException as exc:
        rows.append(("Cache hit ratio", "N/A", f"ERROR ({exc})"))

    return rows


def scenario_concurrency(base_url: str) -> list[tuple[str, str, str]]:
    """Run 5 parallel searches and return table rows."""
    n = 5
    uf_sets = [
        (["SP"], 7),
        (["RJ"], 7),
        (["MG"], 7),
        (["RS"], 7),
        (["BA"], 7),
    ]
    print(f"  Launching {n} parallel searches ...", flush=True)

    t0 = time.monotonic()
    errors = 0
    times: list[float] = []

    with ThreadPoolExecutor(max_workers=n) as executor:
        futures = {
            executor.submit(run_search, base_url, ufs, days): idx
            for idx, (ufs, days) in enumerate(uf_sets)
        }
        for future in as_completed(futures):
            elapsed, status = future.result()
            times.append(elapsed)
            if status != "ok":
                errors += 1

    total_elapsed = time.monotonic() - t0
    rows: list[tuple[str, str, str]] = []

    parallel_verdict = "PASS" if errors == 0 else f"FAIL ({errors} errors)"
    rows.append((f"{n} parallel searches", f"{total_elapsed:.1f}", parallel_verdict))

    error_verdict = "PASS" if errors == 0 else f"FAIL ({errors} errors)"
    rows.append(("Errors", str(errors), error_verdict))

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="BidIQ load test script (SP-001.5)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the BidIQ backend (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--scenarios",
        default="all",
        choices=["latency", "cache", "concurrency", "all"],
        help="Which scenario(s) to run (default: all)",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    today = date.today().isoformat()

    print("=== BidIQ Load Test Results ===")
    print(f"Date:   {today}")
    print(f"Server: {base_url}")

    # Connectivity check
    try:
        requests.get(f"{base_url}/health", timeout=5)
    except requests.RequestException:
        # /health may not exist — try root
        try:
            requests.get(base_url, timeout=5)
        except requests.RequestException as exc:
            print(f"\nERROR: Cannot reach server at {base_url}: {exc}")
            return 1

    all_pass = True
    headers = ("Scenario", "Time (s)", "Status")

    if args.scenarios in ("latency", "all"):
        rows = scenario_latency(base_url)
        print_table("Latency Tests", headers, rows)
        if any("FAIL" in r[2] for r in rows):
            all_pass = False

    if args.scenarios in ("cache", "all"):
        rows = scenario_cache(base_url)
        print_table("Cache Tests", headers, rows)
        if any("FAIL" in r[2] or "ERROR" in r[2] for r in rows):
            all_pass = False

    if args.scenarios in ("concurrency", "all"):
        rows = scenario_concurrency(base_url)
        print_table("Concurrency Tests", headers, rows)
        if any("FAIL" in r[2] for r in rows):
            all_pass = False

    print()
    if all_pass:
        print("Result: ALL PASS")
        return 0
    else:
        print("Result: SOME FAILURES — check output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
