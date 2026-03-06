#!/usr/bin/env python3
"""
Audit all sectors against real PNCP data — focus on FALSE POSITIVES.

For each sector:
1. Fetch real data from PNCP API (curl-equivalent)
2. Apply sector keyword+exclusion filters
3. Identify APPROVED items that look like false positives
4. Identify items BLOCKED by exclusion rules (correctly prevented FPs)

Usage:
    cd backend
    python scripts/audit_false_positives.py
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import RetryConfig, setup_logging
from pncp_client import PNCPClient
from filter import normalize_text, match_keywords
from sectors import SECTORS, SectorConfig

setup_logging("INFO")

# --- Config ---
UFS = ["SP", "MG", "RJ"]
DATE_END = date.today()
DATE_START = DATE_END - timedelta(days=7)
MODALIDADE = 6  # Pregao Eletronico


def fetch_pncp_data() -> list[dict]:
    """Fetch raw procurement data from PNCP API."""
    config = RetryConfig(max_retries=3, jitter=True)
    items: list[dict] = []

    print(f"Buscando dados PNCP: {DATE_START} a {DATE_END}")
    print(f"UFs: {', '.join(UFS)} | Modalidade: 6 (Pregao Eletronico)")
    print()

    with PNCPClient(config=config) as client:
        for item in client.fetch_all(
            data_inicial=DATE_START.isoformat(),
            data_final=DATE_END.isoformat(),
            ufs=UFS,
            modalidades=[MODALIDADE],
        ):
            items.append(item)

    print(f"Total de itens brutos: {len(items)}")
    return items


def analyze_sector(items: list[dict], sector: SectorConfig) -> dict:
    """Analyze a sector for false positives."""
    approved = []
    blocked_by_exclusion = []
    suspect_fps = []  # items approved but likely false positives

    for item in items:
        objeto = item.get("objetoCompra", "") or ""
        valor = item.get("valorTotalEstimado")
        uf = item.get("uf", "")
        codigo = item.get("numeroControlePNCP", "")

        # Test with exclusions
        kw_match, kw_found, _score = match_keywords(objeto, sector.keywords, sector.exclusions)
        # Test without exclusions
        kw_match_no_exc, kw_found_no_exc, _score = match_keywords(objeto, sector.keywords, None)

        if kw_match:
            entry = {
                "codigo": codigo,
                "objeto": objeto[:300],
                "valor": valor,
                "uf": uf,
                "keywords": kw_found[:8],
            }
            approved.append(entry)

            # Heuristic: flag potential false positives
            # Items where ONLY generic/short keywords matched
            obj_norm = normalize_text(objeto)
            is_suspect = _check_suspect_fp(obj_norm, kw_found, sector)
            if is_suspect:
                entry["suspect_reason"] = is_suspect
                suspect_fps.append(entry)

        elif not kw_match and kw_match_no_exc:
            # Correctly blocked by exclusion
            blocked_by_exclusion.append({
                "codigo": codigo,
                "objeto": objeto[:300],
                "keywords_would_match": kw_found_no_exc[:5],
            })

    return {
        "sector_id": sector.id,
        "sector_name": sector.name,
        "total_items": len(items),
        "approved": approved,
        "approved_count": len(approved),
        "blocked_by_exclusion": blocked_by_exclusion,
        "blocked_count": len(blocked_by_exclusion),
        "suspect_false_positives": suspect_fps,
        "suspect_count": len(suspect_fps),
    }


def _check_suspect_fp(obj_norm: str, kw_found: list[str], sector: SectorConfig) -> str | None:
    """
    Heuristic check if an approved item might be a false positive.

    Returns a reason string if suspect, None otherwise.
    """
    # Normalize found keywords
    kw_norms = {normalize_text(k) for k in kw_found}

    # Sector-specific FP checks
    if sector.id == "vestuario":
        # "epi" alone without clothing context
        if kw_norms <= {"epi", "epis", "equipamento de protecao individual", "equipamentos de protecao individual"}:
            # Check if it's actually about non-clothing EPI
            non_clothing_epi = ["capacete", "oculos", "protetor auricular", "cinto", "trava queda",
                                "luva de procedimento", "luva nitrilo", "mascara"]
            if any(term in obj_norm for term in non_clothing_epi):
                return "EPI nao-vestuario (capacete/oculos/luvas)"
        # "bota" alone might be industrial/safety boots in wrong context
        if kw_norms == {"bota"} or kw_norms == {"botas"}:
            if "obra" in obj_norm or "construcao" in obj_norm:
                return "Bota em contexto de obra/construcao"

    elif sector.id == "alimentos":
        # "sal" alone
        if kw_norms <= {"sal"}:
            return "Termo 'sal' isolado — pode ser contexto nao-alimentar"
        # "cafe" alone in office supply context
        if kw_norms <= {"cafe", "café"}:
            if "maquina" in obj_norm or "equipamento" in obj_norm:
                return "Cafe em contexto de maquina/equipamento"

    elif sector.id == "informatica":
        # "monitor" alone could be non-IT
        if kw_norms <= {"monitor", "monitores"}:
            if "saude" in obj_norm or "hospital" in obj_norm or "cardiaco" in obj_norm:
                return "Monitor em contexto hospitalar"
        # "servidor" alone
        if kw_norms <= {"servidor", "servidores"}:
            return "Termo 'servidor' isolado — verificar contexto"

    elif sector.id == "limpeza":
        # "limpeza" in non-product context
        if kw_norms <= {"limpeza"}:
            if "urbana" in obj_norm or "publica" in obj_norm:
                return "Limpeza urbana/publica (nao produtos)"

    elif sector.id == "mobiliario":
        # "mesa" alone
        if kw_norms <= {"mesa", "mesas"}:
            return "Termo 'mesa' isolado — verificar contexto"
        # "banco" alone
        if kw_norms <= {"banco", "bancos"}:
            return "Termo 'banco' isolado — verificar contexto"

    elif sector.id == "papelaria":
        # "papel" alone
        if kw_norms <= {"papel", "papeis", "papéis"}:
            return "Termo 'papel' isolado — verificar contexto"
        # "cola" alone
        if kw_norms <= {"cola", "colas"}:
            return "Termo 'cola' isolado — verificar contexto"

    elif sector.id == "engenharia":
        # "ferro" alone
        if kw_norms <= {"ferro"}:
            return "Termo 'ferro' isolado — verificar contexto"
        # "madeira" alone
        if kw_norms <= {"madeira"}:
            return "Termo 'madeira' isolado — verificar contexto"
        # "cobertura" alone
        if kw_norms <= {"cobertura"}:
            return "Termo 'cobertura' isolado — verificar contexto"
        # "piso" alone
        if kw_norms <= {"piso"}:
            if "salarial" in obj_norm or "salario" in obj_norm:
                return "Piso salarial (nao construcao)"

    elif sector.id == "saude":
        # "soro" alone
        if kw_norms <= {"soro"}:
            return "Termo 'soro' isolado — verificar contexto"
        # "reagente" alone
        if kw_norms <= {"reagente", "reagentes"}:
            return "Termo 'reagente' isolado — verificar contexto"

    elif sector.id == "veiculos":
        # "abastecimento" alone
        if kw_norms <= {"abastecimento"}:
            return "Termo 'abastecimento' isolado — verificar contexto"

    elif sector.id == "hospitalar":
        # "maca" alone could be non-medical
        if kw_norms <= {"maca"}:
            return "Termo 'maca' isolado (fruta?) — verificar contexto"

    elif sector.id == "seguranca":
        # "alarme" alone
        if kw_norms <= {"alarme"}:
            return "Termo 'alarme' isolado — verificar contexto"
        # "ronda" alone
        if kw_norms <= {"ronda"}:
            return "Termo 'ronda' isolado — verificar contexto"
        # "escolta" alone
        if kw_norms <= {"escolta"}:
            return "Termo 'escolta' isolado — verificar contexto"

    elif sector.id == "servicos_gerais":
        # "terceirizacao" alone
        if kw_norms <= {"terceirizacao", "terceirização"}:
            return "Termo 'terceirizacao' isolado — verificar contexto"

    return None


def print_report(results: list[dict]):
    """Print comprehensive report."""
    print("\n" + "=" * 80)
    print("  AUDITORIA DE FALSOS POSITIVOS — PNCP")
    print(f"  Periodo: {DATE_START} a {DATE_END} | UFs: {', '.join(UFS)}")
    print("=" * 80)

    # Summary table
    print(f"\n{'Setor':<35} {'Aprov':>6} {'Bloq':>6} {'Susp FP':>8}")
    print("-" * 60)
    total_approved = 0
    total_blocked = 0
    total_suspect = 0

    for r in results:
        print(f"{r['sector_name']:<35} {r['approved_count']:>6} "
              f"{r['blocked_count']:>6} {r['suspect_count']:>8}")
        total_approved += r["approved_count"]
        total_blocked += r["blocked_count"]
        total_suspect += r["suspect_count"]

    print("-" * 60)
    print(f"{'TOTAL':<35} {total_approved:>6} {total_blocked:>6} {total_suspect:>8}")

    # Detail per sector
    for r in results:
        if r["suspect_count"] == 0 and r["blocked_count"] == 0:
            continue

        print(f"\n{'='*80}")
        print(f"  {r['sector_name']} ({r['sector_id']})")
        print(f"{'='*80}")

        # Suspect false positives (approved but questionable)
        if r["suspect_false_positives"]:
            print(f"\n  SUSPEITOS DE FALSO POSITIVO ({r['suspect_count']}):")
            print(f"  {'—'*70}")
            for i, fp in enumerate(r["suspect_false_positives"][:15]):
                val_str = f"R$ {fp['valor']:,.2f}" if fp['valor'] else "N/A"
                print(f"\n  FP-{i+1}. [{fp['uf']}] {val_str}")
                print(f"    Objeto: {fp['objeto'][:200]}")
                print(f"    Keywords: {', '.join(fp['keywords'][:5])}")
                print(f"    Motivo suspeito: {fp['suspect_reason']}")

        # Correctly blocked by exclusion
        if r["blocked_by_exclusion"]:
            print(f"\n  CORRETAMENTE BLOQUEADOS POR EXCLUSAO ({r['blocked_count']}):")
            print(f"  {'—'*70}")
            for i, b in enumerate(r["blocked_by_exclusion"][:10]):
                print(f"\n  BLQ-{i+1}. {b['objeto'][:200]}")
                print(f"    Keywords bloqueadas: {', '.join(b['keywords_would_match'][:5])}")

        # Sample of approved items (to manually verify)
        if r["approved"]:
            print(f"\n  AMOSTRA DE APROVADOS ({min(10, r['approved_count'])} de {r['approved_count']}):")
            print(f"  {'—'*70}")
            for i, a in enumerate(r["approved"][:10]):
                val_str = f"R$ {a['valor']:,.2f}" if a['valor'] else "N/A"
                print(f"\n  OK-{i+1}. [{a['uf']}] {val_str}")
                print(f"    Objeto: {a['objeto'][:200]}")
                print(f"    Keywords: {', '.join(a['keywords'][:5])}")


def main():
    items = fetch_pncp_data()
    if not items:
        print("ERRO: Nenhum item retornado do PNCP.")
        sys.exit(1)

    results = []
    for sector in SECTORS.values():
        print(f"  Analisando setor: {sector.name}...")
        r = analyze_sector(items, sector)
        results.append(r)

    print_report(results)

    # Save JSON for further analysis
    output_path = Path(__file__).parent / "audit_false_positives.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nDetalhes salvos em: {output_path}")


if __name__ == "__main__":
    main()
