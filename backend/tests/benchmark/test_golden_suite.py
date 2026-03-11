"""Golden test suite for search quality measurement (v3-story-1.2).

This module defines 100 manually curated procurement descriptions:
- 50 known-relevant items (should be APPROVED by the vestuario filter)
- 50 known-irrelevant items (should be REJECTED by the vestuario filter)

These serve as a regression safety net and quality baseline for the
keyword filter engine. Any change to filter.py or sectors.py should
be validated against this suite before merging.

Scoring reference (tier mode, vestuario):
  - Tier A keywords: score = max(score, 1.0)  -> instant approve
  - Tier B keywords: score = max(score, 0.7)  -> approve (threshold=0.6)
  - Tier C keywords: score += 0.3 (additive, capped at 1.0) -> need 2+ to approve
  - Exclusions: checked first, any match -> instant reject
"""

import pytest

from filter import EPI_ONLY_KEYWORDS, match_keywords
from sectors import SECTORS

# Get vestuario sector configuration
VESTUARIO = SECTORS["vestuario"]


def _run_match(objeto: str):
    """Helper to call match_keywords with vestuario config."""
    return match_keywords(
        objeto,
        VESTUARIO.keywords,
        VESTUARIO.exclusions,
        epi_only_keywords=EPI_ONLY_KEYWORDS,
        keywords_a=VESTUARIO.keywords_a,
        keywords_b=VESTUARIO.keywords_b,
        keywords_c=VESTUARIO.keywords_c,
        threshold=VESTUARIO.threshold,
    )


# ============================================================================
# 50 KNOWN-RELEVANT ITEMS (should be APPROVED)
# ============================================================================
GOLDEN_RELEVANT = [
    # --- Tier A: clear uniform/apparel terms (score=1.0) ---
    ("Aquisicao de uniformes escolares para alunos da rede municipal", "Tier A: uniformes"),
    ("Fornecimento de fardamento para guardas municipais", "Tier A: fardamento"),
    ("Confeccao de camisetas para servidores da secretaria de saude", "Tier A: camisetas"),
    ("Aquisicao de jalecos e calcas para profissionais de enfermagem", "Tier A: jalecos, calcas"),
    ("Fornecimento de vestuario profissional para agentes de limpeza", "Tier A: vestuario profissional"),
    ("Kit uniforme escolar: camiseta, bermuda e meia", "Tier A: uniforme, camiseta, bermuda"),
    ("Confeccao de uniformes esportivos para atletas municipais", "Tier A: uniformes esportivos"),
    ("Aquisicao de calcas e bermudas para funcionarios da prefeitura", "Tier A: calcas, bermudas"),
    ("Registro de precos para aquisicao de uniformes para saude", "Tier A: uniformes"),
    ("Pregao eletronico para fornecimento de fardamento escolar", "Tier A: fardamento escolar"),
    ("Aquisicao de vestimentas para equipe de enfermagem do hospital", "Tier A: vestimentas"),
    ("Contratacao de empresa para confeccao de uniformes administrativos", "Tier A: uniformes administrativos"),
    ("Fornecimento de roupas profissionais para motoristas do transporte escolar", "Tier A: roupas profissionais"),
    ("Aquisicao de macacoes para mecanicos da oficina municipal", "Tier A: macacoes"),
    ("Pregao para fornecimento de saias e blusas para atendentes", "Tier A: saias + Tier B: blusas"),
    ("Aquisicao de sapatos para servidores da secretaria de educacao", "Tier A: sapatos"),
    ("Fornecimento de indumentaria para banda musical da guarda", "Tier A: indumentaria"),
    ("Aquisicao de guarda-po para laboratoristas da rede municipal", "Tier A: guarda-po"),
    ("Registro de precos para bermudas e camisetas escolares", "Tier A: bermudas, camisetas"),
    ("Fornecimento de fardas para agentes de seguranca patrimonial", "Tier A: fardas"),
    ("Aquisicao de vestuario para equipe de limpeza urbana", "Tier A: vestuario"),
    ("Pregao eletronico para aquisicao de jalecos hospitalares", "Tier A: jalecos"),
    ("Contratacao para confeccao de uniformes da guarda civil municipal", "Tier A: uniformes"),
    ("Fornecimento de roupa profissional para cozinheiros e auxiliares", "Tier A: roupa profissional"),
    ("Aquisicao de conjunto uniforme para agentes comunitarios de saude", "Tier A: conjunto uniforme"),
    # --- Tier B: strong clothing terms (score=0.7, passes 0.6 threshold) ---
    ("Aquisicao de gandolas e calcas para policia militar", "Tier A: calcas + Tier B: gandolas"),
    ("Fornecimento de camisas polo para servidores publicos", "Tier B: camisas polo"),
    ("Aquisicao de agasalhos para alunos da rede municipal de ensino", "Tier B: agasalhos"),
    ("Pregao para fornecimento de jaquetas para equipe de fiscalizacao", "Tier B: jaquetas"),
    ("Aquisicao de bones para guardas municipais", "Tier B: bones"),
    ("Fornecimento de blusas termicas para servidores da defesa civil", "Tier B: blusas"),
    ("Aquisicao de camisas sociais para funcionarios do gabinete", "Tier B: camisas"),
    ("Pregao eletronico para jardineiras infantis para creches municipais", "Tier B: jardineiras"),
    ("Fornecimento de gandolas camufladas para guarda municipal", "Tier B: gandolas"),
    ("Aquisicao de epi vestuario para trabalhadores da construcao", "Tier B: epi vestuario"),
    # --- Tier C additive: 2+ ambiguous terms reaching threshold ---
    (
        "Aquisicao de coletes e aventais para equipe de cozinha escolar",
        "Tier C additive: coletes(0.3)+aventais(0.3)=0.6",
    ),
    (
        "Fornecimento de botas e meias para trabalhadores rurais do municipio",
        "Tier C additive: botas(0.3)+meias(0.3)=0.6",
    ),
    ("Aquisicao de aventais e coletes para equipe de almoxarifado", "Tier C additive: aventais(0.3)+coletes(0.3)=0.6"),
    ("Fornecimento de coletes, botas e aventais para equipe de cozinha", "Tier C additive: coletes+botas+aventais=0.9"),
    ("Aquisicao de meias e botas para carteiros do servico postal", "Tier C additive: meias(0.3)+botas(0.3)=0.6"),
    # --- Mixed tiers ---
    ("Fornecimento de epi jaleco e calca para profissionais de saude", "Tier A: jaleco, calca + Tier C: epi"),
    (
        "Aquisicao de uniforme completo: camiseta, calca, meia e bota",
        "Tier A: uniforme, camiseta, calca + Tier C: meia, bota",
    ),
    ("Pregao para camisetas e bones para evento esportivo municipal", "Tier A: camisetas + Tier B: bones"),
    ("Fornecimento de jalecos, aventais e toucas para cozinha hospitalar", "Tier A: jalecos + Tier C: aventais"),
    ("Aquisicao de fardamento completo com gandola e coturno", "Tier A: fardamento + Tier B: gandola"),
    (
        "Registro de precos para uniformes, camisas e agasalhos escolares",
        "Tier A: uniformes + Tier B: camisas, agasalhos",
    ),
    ("Confeccao de camisetas e bermudas para projeto social", "Tier A: camisetas, bermudas"),
    ("Aquisicao de vestimenta de protecao para bombeiros municipais", "Tier A: vestimenta"),
    ("Fornecimento de roupas e calcados para funcionarios da saude", "Tier A: roupas"),
    ("Pregao para aquisicao de uniformes e epis para equipe de manutencao", "Tier A: uniformes + Tier C: epis"),
]

# ============================================================================
# 50 KNOWN-IRRELEVANT ITEMS (should be REJECTED)
# ============================================================================
GOLDEN_IRRELEVANT = [
    # --- Exclusion matches (term present but in non-clothing context) ---
    ("Confeccao de placas de sinalizacao para vias urbanas", "Exclusion: confeccao de placas"),
    ("Uniformizacao de procedimentos administrativos na secretaria", "Exclusion: uniformizacao de procedimento"),
    ("Malha viaria para pavimentacao de estradas rurais", "Exclusion: malha viaria"),
    ("Roupa de cama mesa e banho para hospital municipal", "Exclusion: cama mesa e banho"),
    ("Colete balistico para policia militar e guarda municipal", "Exclusion: colete balistico"),
    ("Bota de concreto para construcao civil e pavimentacao", "Exclusion: bota de concreto"),
    ("Meia entrada para eventos culturais e esportivos", "Exclusion: meia entrada"),
    ("Confeccao de proteses dentarias para pacientes do sus", "Exclusion: confeccao de protese"),
    ("Confeccao de chaves para predios publicos municipais", "Exclusion: confeccao de chaves"),
    ("Confeccao de grades para protecao de janelas escolares", "Exclusion: confeccao de grades"),
    ("Confeccao de materiais graficos para campanha de vacinacao", "Exclusion: confeccao de materiais graficos"),
    ("Colete salva vidas para equipe de salvamento aquatico", "Exclusion: colete salva vidas"),
    ("Avental plumbifero para setor de radiologia do hospital", "Exclusion: avental plumbifero"),
    ("Confeccao e instalacao de estruturas metalicas para galpao", "Exclusion: confeccao e instalacao"),
    ("Roupa de cama para abrigo municipal de idosos", "Exclusion: roupa de cama"),
    ("Curso de corte e costura para jovens aprendizes", "Exclusion: curso de corte"),
    ("Material de construcao para reforma de escola municipal", "Exclusion: material de construcao"),
    ("Sinalizacao visual para estacionamento publico municipal", "Exclusion: sinalizacao visual"),
    ("Confeccao de embalagens para kits de higiene pessoal", "Exclusion: confeccao de embalagens"),
    ("Malha rodoviaria para acesso a zona industrial", "Exclusion: malha rodoviaria"),
    # --- No keyword matches at all (unrelated sectors) ---
    ("Aquisicao de computadores e monitores para laboratorio de informatica", "No match: informatica"),
    ("Fornecimento de medicamentos para ubs do municipio", "No match: medicamentos"),
    ("Contratacao de servico de transporte escolar para zona rural", "No match: transporte"),
    ("Aquisicao de mobiliario para escritorios da prefeitura", "No match: mobiliario"),
    ("Fornecimento de combustivel para frota municipal", "No match: combustivel"),
    ("Contratacao de empresa de vigilancia patrimonial armada", "No match: vigilancia"),
    ("Aquisicao de material de limpeza e higienizacao", "No match: limpeza"),
    ("Pregao para contratacao de servicos de engenharia civil", "No match: engenharia"),
    ("Aquisicao de veiculos para secretaria de saude", "No match: veiculos"),
    ("Fornecimento de papel sulfite e material de expediente", "No match: expediente"),
    ("Contratacao de servicos de manutencao predial", "No match: manutencao"),
    ("Aquisicao de equipamentos odontologicos para ubs", "No match: odontologico"),
    ("Fornecimento de pneus para veiculos da frota municipal", "No match: pneus"),
    ("Contratacao de servicos de coleta de residuos solidos", "No match: residuos"),
    ("Aquisicao de licencas de software para gestao escolar", "No match: software"),
    ("Fornecimento de generos alimenticios para merenda escolar", "No match: alimentos"),
    ("Contratacao de servicos de telefonia e internet", "No match: telefonia"),
    ("Aquisicao de instrumentos musicais para banda municipal", "No match: instrumentos"),
    ("Pregao eletronico para servicos de lavanderia hospitalar", "No match: lavanderia"),
    ("Aquisicao de brinquedos pedagogicos para creches municipais", "No match: brinquedos"),
    # --- Single Tier C keyword (score=0.3, below 0.6 threshold) ---
    ("Aquisicao de botas de borracha para uso em lavouras", "Single Tier C: bota (0.3)"),
    ("Fornecimento de meias esportivas para escolinha de futebol", "Single Tier C: meias (0.3)"),
    ("Aquisicao de aventais descartaveis para laboratorio quimico", "Single Tier C: aventais (0.3)"),
    ("Fornecimento de coletes refletivos para equipe de transito", "Single Tier C: coletes (0.3)"),
    (
        "Aquisicao de equipamento de protecao individual para eletricistas",
        "Single Tier C: equipamento de protecao individual (0.3)",
    ),
    # --- EPI-only in tier mode (still just Tier C, score=0.3) ---
    ("Fornecimento de epis para trabalhadores da construcao civil", "Single Tier C: epis (0.3)"),
    ("Aquisicao de epi capacetes luvas e oculos de protecao", "Single Tier C: epi (0.3)"),
    (
        "Fornecimento de equipamentos de protecao individual capacetes e luvas",
        "Single Tier C: equipamentos de protecao individual (0.3)",
    ),
    # --- Decoracao / fantasia exclusions ---
    ("Aquisicao de fantasias para festa junina da escola municipal", "Exclusion: fantasias"),
    ("Servico de decoracao para eventos oficiais da prefeitura", "Exclusion: decoracao"),
]


class TestGoldenSuiteRelevant:
    """All 50 known-relevant items must be APPROVED."""

    @pytest.mark.parametrize(
        "objeto,reason",
        GOLDEN_RELEVANT,
        ids=[f"R{i + 1}" for i in range(len(GOLDEN_RELEVANT))],
    )
    def test_relevant_item_approved(self, objeto, reason):
        approved, matched, score = _run_match(objeto)
        assert approved, f"Expected APPROVED: {objeto}\n  reason: {reason}\n  score:  {score}\n  matched: {matched}"


class TestGoldenSuiteIrrelevant:
    """All 50 known-irrelevant items must be REJECTED."""

    @pytest.mark.parametrize(
        "objeto,reason",
        GOLDEN_IRRELEVANT,
        ids=[f"I{i + 1}" for i in range(len(GOLDEN_IRRELEVANT))],
    )
    def test_irrelevant_item_rejected(self, objeto, reason):
        approved, matched, score = _run_match(objeto)
        assert not approved, f"Expected REJECTED: {objeto}\n  reason: {reason}\n  score:  {score}\n  matched: {matched}"


class TestGoldenSuiteMetrics:
    """Compute and assert precision/recall metrics for the full golden suite."""

    def test_precision_and_recall(self):
        tp = fp = fn = tn = 0

        for objeto, reason in GOLDEN_RELEVANT:
            approved, _, _ = _run_match(objeto)
            if approved:
                tp += 1
            else:
                fn += 1

        for objeto, reason in GOLDEN_IRRELEVANT:
            approved, _, _ = _run_match(objeto)
            if approved:
                fp += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        print(f"\n{'=' * 60}")
        print("GOLDEN SUITE METRICS (v3-story-1.2 baseline)")
        print(f"{'=' * 60}")
        print(f"True Positives (relevant approved):   {tp}")
        print(f"False Positives (irrelevant approved): {fp}")
        print(f"False Negatives (relevant rejected):   {fn}")
        print(f"True Negatives (irrelevant rejected):  {tn}")
        print(f"{'=' * 60}")
        print(f"Precision: {precision:.4f}")
        print(f"Recall:    {recall:.4f}")
        print(f"F1 Score:  {f1:.4f}")
        print(f"{'=' * 60}")

        # Minimum quality thresholds
        assert precision >= 0.90, f"Precision {precision:.4f} below 0.90 threshold"
        assert recall >= 0.90, f"Recall {recall:.4f} below 0.90 threshold"

    def test_suite_size(self):
        """Ensure the golden suite has exactly 100 items."""
        assert len(GOLDEN_RELEVANT) == 50, f"Expected 50 relevant items, got {len(GOLDEN_RELEVANT)}"
        assert len(GOLDEN_IRRELEVANT) == 50, f"Expected 50 irrelevant items, got {len(GOLDEN_IRRELEVANT)}"
