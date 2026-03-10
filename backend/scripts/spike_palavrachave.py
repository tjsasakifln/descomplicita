"""
v3-story-1.0 Spike: PNCP palavraChave Parameter Investigation

Tests whether the PNCP API's `palavraChave` parameter filters results server-side.
Compares response counts with and without the parameter using real search terms.
"""

import httpx
import json
import time
from datetime import date, timedelta

BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
HEADERS = {
    "User-Agent": "Descomplicita/1.0 (spike-test)",
    "Accept": "application/json",
}


def fetch(params: dict, label: str) -> dict:
    """Make a single request and return response data."""
    print(f"\n--- {label} ---")
    print(f"Params: {params}")
    start = time.time()
    try:
        with httpx.Client(timeout=30, headers=HEADERS) as client:
            resp = client.get(BASE_URL, params=params)
        elapsed = time.time() - start
        print(f"Status: {resp.status_code} ({elapsed:.1f}s)")

        if resp.status_code == 200:
            data = resp.json()
            total = data.get("totalRegistros", 0)
            page_items = len(data.get("data", []))
            total_pages = data.get("totalPaginas", 0)
            print(f"Total registros: {total}")
            print(f"Items on page: {page_items}")
            print(f"Total pages: {total_pages}")
            # Sample first 3 objects for inspection
            if page_items > 0:
                print("Sample objects:")
                for i, item in enumerate(data["data"][:3]):
                    obj = item.get("objetoCompra", "N/A")
                    print(f"  [{i+1}] {obj[:120]}")
            return {
                "status": 200,
                "totalRegistros": total,
                "totalPaginas": total_pages,
                "pageItems": page_items,
                "sampleObjects": [
                    item.get("objetoCompra", "") for item in data.get("data", [])[:5]
                ],
            }
        elif resp.status_code == 204:
            print("No content (204)")
            return {"status": 204, "totalRegistros": 0, "totalPaginas": 0, "pageItems": 0}
        else:
            print(f"Error body: {resp.text[:300]}")
            return {"status": resp.status_code, "error": resp.text[:300]}
    except Exception as e:
        elapsed = time.time() - start
        print(f"Exception after {elapsed:.1f}s: {type(e).__name__}: {e}")
        return {"status": "error", "error": str(e)}


def run_spike():
    """Execute the palavraChave spike test."""
    # Use a recent 7-day window
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    d_ini = start_date.strftime("%Y%m%d")
    d_fin = end_date.strftime("%Y%m%d")

    results = {}

    # ===== Test 1: Baseline WITHOUT palavraChave =====
    base_params = {
        "dataInicial": d_ini,
        "dataFinal": d_fin,
        "codigoModalidadeContratacao": 6,  # Pregão Eletrônico
        "uf": "SP",
        "pagina": 1,
        "tamanhoPagina": 50,
    }
    results["baseline"] = fetch(base_params, "BASELINE (no palavraChave)")

    time.sleep(1)

    # ===== Test 2: WITH palavraChave = "uniforme" =====
    params_kw1 = {**base_params, "palavraChave": "uniforme"}
    results["with_uniforme"] = fetch(params_kw1, 'WITH palavraChave="uniforme"')

    time.sleep(1)

    # ===== Test 3: WITH palavraChave = "confeccao" =====
    params_kw2 = {**base_params, "palavraChave": "confeccao"}
    results["with_confeccao"] = fetch(params_kw2, 'WITH palavraChave="confeccao"')

    time.sleep(1)

    # ===== Test 4: WITH palavraChave = "xyzzy_nonexistent_term_12345" =====
    # If filtering works, this should return 0 results
    params_kw3 = {**base_params, "palavraChave": "xyzzy_nonexistent_term_12345"}
    results["with_nonsense"] = fetch(params_kw3, 'WITH palavraChave="xyzzy_nonexistent_term_12345"')

    time.sleep(1)

    # ===== Test 5: Try "palavra_chave" variant =====
    params_kw4 = {**base_params, "palavra_chave": "uniforme"}
    results["with_palavra_chave"] = fetch(params_kw4, 'WITH palavra_chave="uniforme" (underscore variant)')

    time.sleep(1)

    # ===== Test 6: Try "q" query param =====
    params_kw5 = {**base_params, "q": "uniforme"}
    results["with_q"] = fetch(params_kw5, 'WITH q="uniforme"')

    time.sleep(1)

    # ===== Test 7: Try with accented term "confecção" =====
    params_kw6 = {**base_params, "palavraChave": "confecção"}
    results["with_confeccao_accented"] = fetch(params_kw6, 'WITH palavraChave="confecção" (accented)')

    # ===== Analysis =====
    print("\n" + "=" * 60)
    print("SPIKE ANALYSIS")
    print("=" * 60)

    baseline_total = results.get("baseline", {}).get("totalRegistros", -1)
    uniforme_total = results.get("with_uniforme", {}).get("totalRegistros", -1)
    confeccao_total = results.get("with_confeccao", {}).get("totalRegistros", -1)
    nonsense_total = results.get("with_nonsense", {}).get("totalRegistros", -1)
    underscore_total = results.get("with_palavra_chave", {}).get("totalRegistros", -1)
    q_total = results.get("with_q", {}).get("totalRegistros", -1)
    accented_total = results.get("with_confeccao_accented", {}).get("totalRegistros", -1)

    print(f"\nBaseline (no keyword):      {baseline_total} registros")
    print(f"With 'uniforme':            {uniforme_total} registros")
    print(f"With 'confeccao':           {confeccao_total} registros")
    print(f"With nonsense term:         {nonsense_total} registros")
    print(f"With 'palavra_chave' param: {underscore_total} registros")
    print(f"With 'q' param:             {q_total} registros")
    print(f"With accented 'confecção':  {accented_total} registros")

    filtering_works = False

    if baseline_total > 0:
        if uniforme_total < baseline_total or confeccao_total < baseline_total:
            print("\n[POSITIVE] palavraChave DOES filter results!")
            print(f"   Reduction: {baseline_total} -> {uniforme_total} (uniforme)")
            print(f"   Reduction: {baseline_total} -> {confeccao_total} (confeccao)")
            filtering_works = True
        elif nonsense_total == 0 and baseline_total > 0:
            print("\n[POSITIVE] palavraChave filters (nonsense returned 0)")
            filtering_works = True
        else:
            print("\n[NEGATIVE] palavraChave is silently ignored")
            print("   All requests return the same totalRegistros regardless of keyword")

    if nonsense_total == baseline_total and baseline_total > 0:
        print("   Confirmed: nonsense term returns same count as baseline")

    print(f"\nFILTERING WORKS: {filtering_works}")

    # Save results
    output = {
        "spike": "v3-story-1.0",
        "date_range": f"{d_ini}-{d_fin}",
        "filtering_works": filtering_works,
        "results": results,
    }

    output_path = "backend/scripts/spike_palavrachave_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to {output_path}")

    return filtering_works


if __name__ == "__main__":
    run_spike()
