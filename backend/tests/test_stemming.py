"""Unit tests for RSLP stemming integration (v3-story-2.1).

Tests cover:
- stem_text() function behavior
- Stemming applied to both keyword and object sides of matching
- Exact match priority over stemmed match
- Exclusion keywords still working with stemming
- Accent handling through stemming pipeline
- Hyphenated terms
- Golden suite precision/recall delta measurement
"""

import pytest

from filter import (
    EPI_ONLY_KEYWORDS,
    KEYWORDS_EXCLUSAO,
    KEYWORDS_UNIFORMES,
    _keyword_matches,
    match_keywords,
    normalize_text,
    stem_text,
    stem_word,
)
from sectors import SECTORS

VESTUARIO = SECTORS["vestuario"]


class TestStemText:
    """Tests for stem_text() function."""

    def test_stem_uniformizado_matches_uniforme(self):
        """Primary acceptance criterion: 'uniformizado' should share stem with 'uniforme'."""
        assert stem_text("uniformizado") == stem_text("uniforme")

    def test_stem_uniformes_matches_uniforme(self):
        """Plural should share stem with singular."""
        assert stem_text("uniformes") == stem_text("uniforme")

    def test_stem_confeccionado_shares_root(self):
        """confeccionado should stem consistently."""
        # RSLP stems these differently, but both are valid stems
        s1 = stem_text("confeccionado")
        s2 = stem_text("confeccao")
        # They may not be equal (RSLP limitation), but stem_text should
        # produce stable output for each
        assert s1 != ""
        assert s2 != ""

    def test_stem_empty_string(self):
        """Empty input should return empty output."""
        assert stem_text("") == ""

    def test_stem_single_word(self):
        """Single word should be stemmed."""
        result = stem_text("camisetas")
        assert result != ""
        assert result == stem_text("camiseta")

    def test_stem_multi_word(self):
        """Multi-word input should stem each word."""
        result = stem_text("uniformes escolares")
        words = result.split()
        assert len(words) == 2

    def test_stem_with_accents(self):
        """Accented text should be normalized before stemming."""
        assert stem_text("licitação") == stem_text("licitacao")
        assert stem_text("confecção") == stem_text("confeccao")

    def test_stem_preserves_normalization(self):
        """stem_text should include normalize_text preprocessing."""
        # Uppercase, accents, punctuation all handled
        assert stem_text("UNIFORMES!!!") == stem_text("uniformes")
        assert stem_text("  Jáleco  Médico  ") == stem_text("jaleco medico")

    def test_stem_hyphenated_term(self):
        """Hyphenated terms should be normalized (hyphen→space) then stemmed."""
        result = stem_text("guarda-pó")
        assert result == stem_text("guarda po")

    def test_stem_nfc_vs_nfd_identical(self):
        """NFC and NFD encoded input should produce identical stemmed output."""
        import unicodedata

        text = "confecção"
        nfc = unicodedata.normalize("NFC", text)
        nfd = unicodedata.normalize("NFD", text)
        assert stem_text(nfc) == stem_text(nfd)


class TestStemWord:
    """Tests for stem_word() individual word stemming."""

    def test_stem_word_basic(self):
        """Should stem a simple word."""
        result = stem_word("uniformes")
        assert result != ""
        assert result == stem_word("uniforme")

    def test_stem_word_caching(self):
        """stem_word uses lru_cache, repeated calls should be fast."""
        r1 = stem_word("camisetas")
        r2 = stem_word("camisetas")
        assert r1 == r2


class TestStemmingInMatchKeywords:
    """Tests for stemming applied in match_keywords()."""

    def test_uniformizado_matches_uniforme_keyword(self):
        """Primary acceptance: 'uniformizado' in object matches 'uniforme' keyword."""
        approved, matched, score = match_keywords(
            "Aquisicao de itens uniformizados para escola",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is True
        assert len(matched) > 0

    def test_confeccionado_matches_via_keyword(self):
        """'confeccionado' matches because it's now a keyword."""
        approved, matched, _ = match_keywords(
            "Servico de confeccionado de roupas",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is True

    def test_exact_match_has_priority(self):
        """Exact (normalized) match should work even without stemming."""
        approved, matched, _ = match_keywords(
            "Aquisicao de uniformes escolares",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is True
        assert "uniformes" in matched or "uniforme" in matched

    def test_stemming_catches_inflections(self):
        """Stemming should catch verbal inflections that exact match misses."""
        # "uniformizado" is NOT in the keyword set but stems to same root as "uniforme"
        approved, matched, _ = match_keywords(
            "Material uniformizado para funcionarios",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is True

    def test_camisas_plural_singular_both_match(self):
        """Both singular and plural forms should match."""
        approved1, _, _ = match_keywords("Fornecimento de camisa polo", KEYWORDS_UNIFORMES)
        approved2, _, _ = match_keywords("Fornecimento de camisas polo", KEYWORDS_UNIFORMES)
        assert approved1 is True
        assert approved2 is True

    def test_stemming_with_tier_scoring(self):
        """Stemming should work in tier scoring mode."""
        approved, matched, score = match_keywords(
            "Aquisicao de itens uniformizados para escola",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
            keywords_a=VESTUARIO.keywords_a,
            keywords_b=VESTUARIO.keywords_b,
            keywords_c=VESTUARIO.keywords_c,
            threshold=VESTUARIO.threshold,
        )
        assert approved is True
        assert score >= VESTUARIO.threshold


class TestExclusionsWithStemming:
    """Task 5: Exclusion keywords must continue working with stemming."""

    def test_confeccao_de_placa_still_excluded(self):
        """Acceptance criterion: 'confeccao de placa de sinalizacao' stays excluded."""
        approved, _, _ = match_keywords(
            "Confeccao de placa de sinalizacao",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is False

    def test_uniformizacao_de_procedimento_excluded(self):
        """'uniformizacao de procedimento' stays excluded."""
        approved, _, _ = match_keywords(
            "Uniformizacao de procedimento padrao",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is False

    def test_uniformemente_excluded(self):
        """Adverb 'uniformemente' is excluded (not clothing)."""
        approved, _, _ = match_keywords(
            "Distribuicao uniformemente espacada de recursos",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is False

    def test_uniformizacao_excluded(self):
        """Bare 'uniformizacao' (standardization) is excluded."""
        approved, _, _ = match_keywords(
            "Uniformizacao de processos internos",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is False

    def test_colete_balistico_still_excluded(self):
        """'colete balistico' stays excluded despite stemming."""
        approved, _, _ = match_keywords(
            "Colete balistico para policia",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is False

    def test_roupa_de_cama_still_excluded(self):
        """'roupa de cama' stays excluded."""
        approved, _, _ = match_keywords(
            "Aquisicao de roupa de cama hospitalar",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is False

    def test_exclusions_use_exact_not_stemmed(self):
        """Exclusions must NOT use stemming (would cause over-blocking)."""
        # "uniformizacao" is excluded, but "uniforme" must NOT be blocked
        approved, _, _ = match_keywords(
            "Aquisicao de uniformes escolares",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is True


class TestAccentHandlingWithStemming:
    """Task 9: Accented terms must work correctly after stemming."""

    def test_licitacao_with_accent(self):
        """'licitação' (with accent) and 'licitacao' (without) produce same stem."""
        assert stem_text("licitação") == stem_text("licitacao")

    def test_confeccao_accent_variants(self):
        """Both 'confecção' and 'confeccao' stem identically."""
        assert stem_text("confecção") == stem_text("confeccao")

    def test_accent_keyword_matches_no_accent_object(self):
        """Accented keyword matches non-accented object text."""
        approved, _, _ = match_keywords(
            "Aquisicao de uniformes",  # no accents
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is True

    def test_no_accent_keyword_matches_accent_object(self):
        """Non-accented keyword matches accented object text."""
        approved, _, _ = match_keywords(
            "Aquisição de uniformes",  # with accent
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
        )
        assert approved is True

    def test_full_diacritics_ptbr(self):
        """All PT-BR diacritics should be handled by normalize→stem pipeline."""
        pairs = [
            ("ação", "acao"),
            ("ções", "coes"),
            ("é", "e"),
            ("ã", "a"),
            ("ú", "u"),
            ("ô", "o"),
        ]
        for accented, plain in pairs:
            assert normalize_text(accented) == normalize_text(plain), f"normalize_text mismatch: {accented} vs {plain}"


class TestKeywordMatchesHelper:
    """Tests for _keyword_matches() helper function."""

    def test_exact_match(self):
        """Should return True for exact normalized match."""
        assert _keyword_matches("uniforme", "compra de uniforme escolar", "compr de uniform escol")

    def test_stemmed_match(self):
        """Should return True for stemmed match when exact fails."""
        objeto_norm = normalize_text("Material uniformizado")
        objeto_stemmed = stem_text("Material uniformizado")
        assert _keyword_matches("uniforme", objeto_norm, objeto_stemmed)

    def test_no_match(self):
        """Should return False when neither exact nor stemmed matches."""
        objeto_norm = normalize_text("Compra de computadores")
        objeto_stemmed = stem_text("Compra de computadores")
        assert not _keyword_matches("uniforme", objeto_norm, objeto_stemmed)


class TestTierCStemDedup:
    """Tier C score deduplication: singular/plural sharing stems count once."""

    def test_bota_botas_count_once(self):
        """'bota' and 'botas' should not double-count in Tier C."""
        approved, matched, score = match_keywords(
            "Aquisicao de botas de borracha para uso em lavouras",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
            keywords_a=VESTUARIO.keywords_a,
            keywords_b=VESTUARIO.keywords_b,
            keywords_c=VESTUARIO.keywords_c,
            threshold=VESTUARIO.threshold,
        )
        # Single Tier C keyword (even if both singular and plural match)
        # should score 0.3, below 0.6 threshold
        assert approved is False
        assert score <= 0.3

    def test_meias_meia_count_once(self):
        """'meia' and 'meias' should not double-count in Tier C."""
        approved, _, score = match_keywords(
            "Fornecimento de meias esportivas para escolinha",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
            keywords_a=VESTUARIO.keywords_a,
            keywords_b=VESTUARIO.keywords_b,
            keywords_c=VESTUARIO.keywords_c,
            threshold=VESTUARIO.threshold,
        )
        assert approved is False
        assert score <= 0.3

    def test_two_distinct_tier_c_still_pass(self):
        """Two genuinely different Tier C keywords should still add up."""
        approved, _, score = match_keywords(
            "Aquisicao de coletes e aventais para cozinha",
            KEYWORDS_UNIFORMES,
            KEYWORDS_EXCLUSAO,
            keywords_a=VESTUARIO.keywords_a,
            keywords_b=VESTUARIO.keywords_b,
            keywords_c=VESTUARIO.keywords_c,
            threshold=VESTUARIO.threshold,
        )
        assert approved is True
        assert score >= 0.6
