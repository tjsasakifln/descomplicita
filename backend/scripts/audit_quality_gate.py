#!/usr/bin/env python3
"""
Automated filter quality gate for CI/CD.

Validates false positive rates across all sectors against configurable thresholds.
Exit codes: 0 = PASS, 1 = FAIL

Usage:
    python scripts/audit_quality_gate.py [--threshold-sector 0.03] [--threshold-global 0.01]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from filter import match_keywords
from sectors import SECTORS

# Known false positive patterns by sector (ground truth from audit 2026-03-05)
# These are test cases derived from real PNCP data
KNOWN_FP_PATTERNS = {
    "limpeza": [
        "Contratação de serviço de limpeza urbana e coleta de resíduos",
        "Aquisição de avental descartável hospitalar",
        "Contratação de limpeza pública de vias e logradouros",
        "Aquisição de campo cirúrgico descartável para centro cirúrgico",
        "Kit cirúrgico descartável para procedimentos",
    ],
    "engenharia": [
        "Implantação de infraestrutura de fibra óptica municipal",
        "Contratação de plano de saúde com cobertura ambulatorial",
        "Seguro com cobertura veicular para frota",
        "Infraestrutura de conectividade para escolas",
        "Cobertura aeronáutica para aeronaves",
    ],
    "informatica": [
        "Capacitação de servidores do município",
        "Materiais destinados aos servidores da prefeitura",
        "Aquisição de monitor de glicose para UBS",
        "Treinamento de servidores das secretarias municipais",
        "Formação de servidores públicos da câmara",
    ],
    "vestuario": [
        "Aquisição de EPI - RESPIRADOR SEMIFACIAL",
        "AQUISICAO DE EPI'S - MASCARA SOLDA, CINTO DE PARAQUEDISTA",
        "Aquisição de material de segurança e EPI/EPC",
    ],
    "alimentos": [
        "Aquisição de óleo de motor para frota municipal",
        "Compra de moinho para café industrial",
        "Aquisição de máquina de café para escritório",
    ],
    "mobiliario": [
        "Aquisição de rack 19 polegadas para datacenter",
        "Contratação de serviços bancários para pagamento de servidores",
    ],
    "veiculos": [
        "Sistema de abastecimento público de água",
    ],
    "seguranca": [
        "Contratação de vigilância de vetores e zoonoses",
        "Serviço de vigilância ambiental em saúde",
    ],
}

# Known true positive patterns (should NOT be blocked)
KNOWN_TP_PATTERNS = {
    "limpeza": [
        "Aquisição de detergente e desinfetante para limpeza",
        "Material de limpeza: saco de lixo, vassoura, rodo",
        "Produtos de limpeza e higienização predial",
    ],
    "engenharia": [
        "Contratação de pavimentação asfáltica",
        "Obra de construção civil — alvenaria e concreto",
        "Reforma e ampliação de escola municipal",
    ],
    "informatica": [
        "Aquisição de notebooks e impressoras",
        "Registro de preços para toner e cartuchos",
        "Servidor rack Dell PowerEdge com nobreak",
    ],
    "vestuario": [
        "Aquisição de uniformes escolares para alunos",
        "Fornecimento de jalecos hospitalares",
        "Confecção de fardamento militar",
    ],
    "alimentos": [
        "AQUISIÇÃO PARCELADA DE CAFÉ PARA O ANO DE 2026",
        "Gêneros alimentícios - merenda escolar",
        "Cesta básica para famílias cadastradas",
    ],
    "mobiliario": [
        "Aquisição de mesas de escritório e cadeiras",
    ],
    "veiculos": [
        "Aquisição de combustível - gasolina e diesel",
    ],
    "seguranca": [
        "Contratação de vigilância patrimonial armada",
    ],
    "papelaria": [
        "Aquisição de material de escritório e papelaria",
    ],
    "saude": [
        "Aquisição de medicamentos e insumos hospitalares",
    ],
    "hospitalar": [
        "Aquisição de equipamento médico hospitalar",
    ],
    "servicos_gerais": [
        "Contratação de serviços gerais e manutenção predial",
    ],
}


def run_audit(threshold_sector: float = 0.03, threshold_global: float = 0.01) -> dict:
    """Run the quality gate audit against known patterns."""
    from filter import EPI_ONLY_KEYWORDS

    results = []
    total_fp = 0
    total_tp = 0
    total_fn = 0
    total_tn = 0

    for sector_id, sector in SECTORS.items():
        fp_patterns = KNOWN_FP_PATTERNS.get(sector_id, [])
        tp_patterns = KNOWN_TP_PATTERNS.get(sector_id, [])

        # Test known FPs — these should all be REJECTED
        fps_caught = 0
        fps_missed = []
        for pattern in fp_patterns:
            epi_kw = EPI_ONLY_KEYWORDS if sector_id == "vestuario" else None
            ok, kw, score = match_keywords(
                pattern,
                sector.keywords,
                sector.exclusions,
                epi_only_keywords=epi_kw,
                keywords_a=sector.keywords_a,
                keywords_b=sector.keywords_b,
                keywords_c=sector.keywords_c,
                threshold=sector.threshold,
            )
            if not ok:
                fps_caught += 1
                total_tn += 1
            else:
                fps_missed.append(pattern)
                total_fp += 1

        # Test known TPs — these should all be APPROVED
        tps_caught = 0
        tps_missed = []
        for pattern in tp_patterns:
            epi_kw = EPI_ONLY_KEYWORDS if sector_id == "vestuario" else None
            ok, kw, score = match_keywords(
                pattern,
                sector.keywords,
                sector.exclusions,
                epi_only_keywords=epi_kw,
                keywords_a=sector.keywords_a,
                keywords_b=sector.keywords_b,
                keywords_c=sector.keywords_c,
                threshold=sector.threshold,
            )
            if ok:
                tps_caught += 1
                total_tp += 1
            else:
                tps_missed.append(pattern)
                total_fn += 1

        total_tested = len(fp_patterns) + len(tp_patterns)
        fp_rate = len(fps_missed) / max(total_tested, 1)

        results.append(
            {
                "sector": sector_id,
                "sector_name": sector.name,
                "fp_patterns_tested": len(fp_patterns),
                "fp_caught": fps_caught,
                "fp_missed": fps_missed,
                "tp_patterns_tested": len(tp_patterns),
                "tp_caught": tps_caught,
                "tp_missed": tps_missed,
                "fp_rate": fp_rate,
                "passed": fp_rate <= threshold_sector and len(tps_missed) == 0,
            }
        )

    total_patterns = total_fp + total_tp + total_tn + total_fn
    global_fp_rate = total_fp / max(total_patterns, 1)

    return {
        "timestamp": datetime.now().isoformat(),
        "thresholds": {"sector": threshold_sector, "global": threshold_global},
        "sectors": results,
        "summary": {
            "total_sectors": len(results),
            "sectors_passed": sum(1 for r in results if r["passed"]),
            "sectors_failed": sum(1 for r in results if not r["passed"]),
            "total_fp_missed": total_fp,
            "total_fn": total_fn,
            "global_fp_rate": global_fp_rate,
            "global_passed": global_fp_rate <= threshold_global and total_fn == 0,
        },
    }


def generate_markdown_report(audit: dict) -> str:
    """Generate markdown report from audit results."""
    lines = []
    lines.append("# Filter Quality Gate Report")
    lines.append(f"\nDate: {audit['timestamp']}")
    lines.append(f"Thresholds: sector={audit['thresholds']['sector']:.1%}, global={audit['thresholds']['global']:.1%}")

    summary = audit["summary"]
    status = "PASSED" if summary["global_passed"] else "FAILED"
    lines.append(f"\n## Result: **{status}**")
    lines.append(f"\n- Sectors: {summary['sectors_passed']}/{summary['total_sectors']} passed")
    lines.append(f"- False positives missed: {summary['total_fp_missed']}")
    lines.append(f"- False negatives: {summary['total_fn']}")
    lines.append(f"- Global FP rate: {summary['global_fp_rate']:.2%}")

    lines.append("\n## Sector Details\n")
    lines.append("| Sector | FP Caught | FP Missed | TP OK | FN | Status |")
    lines.append("|--------|-----------|-----------|-------|----|--------|")

    for r in audit["sectors"]:
        status_label = "PASS" if r["passed"] else "FAIL"
        lines.append(
            f"| {r['sector']} | {r['fp_caught']}/{r['fp_patterns_tested']} "
            f"| {len(r['fp_missed'])} | {r['tp_caught']}/{r['tp_patterns_tested']} "
            f"| {len(r['tp_missed'])} | {status_label} |"
        )

    # Show failures detail
    failures = [r for r in audit["sectors"] if not r["passed"]]
    if failures:
        lines.append("\n## Failures\n")
        for r in failures:
            lines.append(f"### {r['sector_name']}")
            if r["fp_missed"]:
                lines.append("\nFalse positives not caught:")
                for fp in r["fp_missed"]:
                    lines.append(f"- `{fp}`")
            if r["tp_missed"]:
                lines.append("\nFalse negatives (should approve but rejected):")
                for fn in r["tp_missed"]:
                    lines.append(f"- `{fn}`")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Filter quality gate audit")
    parser.add_argument("--threshold-sector", type=float, default=0.03)
    parser.add_argument("--threshold-global", type=float, default=0.01)
    args = parser.parse_args()

    audit = run_audit(args.threshold_sector, args.threshold_global)

    # Write JSON results
    results_path = Path(__file__).parent / "audit_quality_gate_results.json"
    with open(results_path, "w") as f:
        json.dump(audit, f, indent=2)

    # Write markdown report
    report = generate_markdown_report(audit)
    report_path = Path(__file__).parent / "audit_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    # Print summary
    summary = audit["summary"]
    print(report)

    if summary["global_passed"]:
        print("\nQUALITY GATE PASSED")
        sys.exit(0)
    else:
        print("\nQUALITY GATE FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
