"""Tests for Tier C additive scoring in match_keywords (v3-story-1.2 Task 4).

FP3: Single Tier C keyword scores 0.3 (below 0.6 threshold) -> rejected
FP4: Multiple Tier C keywords accumulate (0.3 each) -> can pass threshold
FP5: EPI_ONLY_KEYWORDS check still rejects EPI-only matches in tier scoring
Score capping: score never exceeds 1.0 even with many Tier C matches
"""

import pytest
from filter import match_keywords


# --- Shared fixtures ---

KEYWORDS_A = {"uniforme", "fardamento"}
KEYWORDS_B = {"jaleco", "camisa social"}
KEYWORDS_C = {"epi", "epis", "bota", "botas", "meia", "meias", "avental", "aventais", "colete", "coletes", "confeccao", "costura"}
EPI_ONLY = {"epi", "epis", "equipamento de protecao individual"}
ALL_KEYWORDS = KEYWORDS_A | KEYWORDS_B | KEYWORDS_C


class TestFP3SingleTierCRejected:
    """FP3: A single Tier C keyword alone should score 0.3 and be rejected (< 0.6)."""

    def test_single_tier_c_bota_rejected(self):
        approved, matched, score = match_keywords(
            "Aquisicao de bota para funcionarios",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert not approved
        assert score == pytest.approx(0.3)
        assert "bota" in matched

    def test_single_tier_c_meia_rejected(self):
        approved, matched, score = match_keywords(
            "Fornecimento de meia esportiva",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert not approved
        assert score == pytest.approx(0.3)

    def test_single_tier_c_avental_rejected(self):
        approved, matched, score = match_keywords(
            "Compra de avental descartavel",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert not approved
        assert score == pytest.approx(0.3)


class TestFP4AdditiveTierCScoring:
    """FP4: Multiple Tier C keywords accumulate to pass threshold."""

    def test_three_tier_c_keywords_accepted(self):
        """bota + meia + avental = 0.9 >= 0.6 -> accepted."""
        approved, matched, score = match_keywords(
            "Aquisicao de bota, meia e avental para equipe",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert approved
        assert score == pytest.approx(0.9)
        # Stemming may match both singular and plural forms (e.g., bota+botas)
        assert len(matched) >= 3
        assert {"bota", "meia", "avental"}.issubset(set(matched))

    def test_two_tier_c_keywords_accepted(self):
        """bota + meia = 0.6 >= 0.6 -> accepted (exactly at threshold)."""
        approved, matched, score = match_keywords(
            "Fornecimento de bota e meia para funcionarios",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert approved
        assert score == pytest.approx(0.6)
        # Stemming may match both singular and plural forms
        assert len(matched) >= 2

    def test_single_tier_c_still_rejected(self):
        """bota alone = 0.3 < 0.6 -> rejected (single C still insufficient)."""
        approved, matched, score = match_keywords(
            "Compra de bota de borracha",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert not approved
        assert score == pytest.approx(0.3)


class TestFP5EpiOnlyCheck:
    """FP5: EPI_ONLY_KEYWORDS check still works in binary mode."""

    def test_epi_only_rejected_binary_mode(self):
        """Item with only 'epi' in binary mode -> rejected by EPI-only check."""
        approved, matched, score = match_keywords(
            "Aquisicao de epi para obras",
            keywords=ALL_KEYWORDS,
            epi_only_keywords=EPI_ONLY,
        )
        assert not approved
        assert matched == []
        assert score == 0.0

    def test_epi_plus_jaleco_accepted_binary_mode(self):
        """Item with 'epi + jaleco' in binary mode -> accepted (not EPI-only)."""
        approved, matched, score = match_keywords(
            "Aquisicao de epi e jaleco hospitalar",
            keywords=ALL_KEYWORDS,
            epi_only_keywords=EPI_ONLY,
        )
        assert approved
        assert "epi" in matched
        assert "jaleco" in matched


class TestTierCScoreCapping:
    """Score should never exceed 1.0 even with many Tier C matches."""

    def test_five_tier_c_keywords_capped_at_1(self):
        """5 Tier C matches = min(1.0, 1.5) = 1.0."""
        approved, matched, score = match_keywords(
            "Aquisicao de bota, meia, avental, colete e confeccao",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert approved
        assert score == pytest.approx(1.0)
        # Stemming may match both singular and plural forms
        assert len(matched) >= 5

    def test_four_tier_c_keywords_capped_at_1(self):
        """4 Tier C matches = min(1.0, 1.2) = 1.0."""
        approved, matched, score = match_keywords(
            "Fornecimento de bota, meia, avental e colete",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert approved
        assert score == pytest.approx(1.0)
        # Stemming may match both singular and plural forms
        assert len(matched) >= 4


class TestTierABUnchanged:
    """Verify Tier A and B scoring remains max-based, not additive."""

    def test_tier_a_still_max_based(self):
        """Tier A match gives score 1.0 immediately."""
        approved, matched, score = match_keywords(
            "Confeccao de uniforme escolar",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert approved
        assert score == pytest.approx(1.0)
        assert "uniforme" in matched

    def test_tier_b_still_max_based(self):
        """Tier B match gives score 0.7."""
        approved, matched, score = match_keywords(
            "Aquisicao de jaleco branco",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert approved
        assert score == pytest.approx(0.7)
        assert "jaleco" in matched

    def test_tier_b_plus_tier_c_additive_on_c_only(self):
        """Tier B (0.7) + Tier C (0.3) -> score should reflect B max then C adds.
        Since B sets score=0.7 via max, and C adds 0.3, total = min(1.0, 1.0) = 1.0."""
        approved, matched, score = match_keywords(
            "Aquisicao de jaleco e bota",
            keywords=ALL_KEYWORDS,
            keywords_a=KEYWORDS_A,
            keywords_b=KEYWORDS_B,
            keywords_c=KEYWORDS_C,
            threshold=0.6,
        )
        assert approved
        assert score == pytest.approx(1.0)
        assert "jaleco" in matched
        assert "bota" in matched
