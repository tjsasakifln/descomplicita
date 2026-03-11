"""Unit tests for parse_multi_word_terms (UXD-001).

Function under test: main.parse_multi_word_terms(raw: str) -> list[str]

Covers:
- None / empty / whitespace-only inputs
- Quoted multi-word phrases
- Comma-separated terms (with and without quotes)
- Mixed quoted + unquoted comma-separated terms
- Backward-compatible space-separated terms (no quotes, no commas)
- Lowercase normalisation
- Leading / trailing whitespace handling
- Edge cases: empty segments, consecutive commas, extra spaces
"""

import pytest

from main import parse_multi_word_terms

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sorted(terms: list[str]) -> list[str]:
    """Return a sorted copy for order-insensitive assertions."""
    return sorted(terms)


# ---------------------------------------------------------------------------
# Empty / falsy inputs
# ---------------------------------------------------------------------------


class TestEmptyAndNoneInputs:
    """parse_multi_word_terms must return [] for all empty / falsy inputs."""

    def test_none_returns_empty(self):
        assert parse_multi_word_terms(None) == []  # type: ignore[arg-type]

    def test_empty_string_returns_empty(self):
        assert parse_multi_word_terms("") == []

    def test_single_space_returns_empty(self):
        assert parse_multi_word_terms(" ") == []

    def test_multiple_spaces_returns_empty(self):
        assert parse_multi_word_terms("   ") == []

    def test_tabs_and_newlines_returns_empty(self):
        assert parse_multi_word_terms("\t\n  \t") == []


# ---------------------------------------------------------------------------
# Single term (no quotes, no commas) — backward-compatible space-split path
# ---------------------------------------------------------------------------


class TestSpaceSeparatedTerms:
    """Backward-compatible space-separated path (no quotes, no commas)."""

    def test_single_word(self):
        assert parse_multi_word_terms("jaleco") == ["jaleco"]

    def test_two_words_become_two_terms(self):
        assert parse_multi_word_terms("jaleco avental") == ["jaleco", "avental"]

    def test_three_words(self):
        assert parse_multi_word_terms("jaleco avental luva") == ["jaleco", "avental", "luva"]

    def test_extra_spaces_between_words_are_collapsed(self):
        assert parse_multi_word_terms("jaleco   avental") == ["jaleco", "avental"]

    def test_leading_and_trailing_spaces_stripped(self):
        assert parse_multi_word_terms("  jaleco avental  ") == ["jaleco", "avental"]

    def test_terms_are_lowercased(self):
        assert parse_multi_word_terms("JALECO Avental") == ["jaleco", "avental"]


# ---------------------------------------------------------------------------
# Quoted multi-word phrases
# ---------------------------------------------------------------------------


class TestQuotedTerms:
    """Quoted phrases must be treated as a single term."""

    def test_single_quoted_two_word_term(self):
        assert parse_multi_word_terms('"camisa polo"') == ["camisa polo"]

    def test_single_quoted_three_word_term(self):
        assert parse_multi_word_terms('"jaleco manga longa"') == ["jaleco manga longa"]

    def test_quoted_term_is_lowercased(self):
        assert parse_multi_word_terms('"Camisa Polo"') == ["camisa polo"]

    def test_quoted_term_with_inner_whitespace_stripped(self):
        # The CSV reader strips outer spaces; inner spaces belong to the phrase.
        assert parse_multi_word_terms('"  camisa polo  "') == ["camisa polo"]

    def test_quoted_term_with_outer_whitespace(self):
        assert parse_multi_word_terms('  "camisa polo"  ') == ["camisa polo"]

    def test_single_word_in_quotes(self):
        # A single word wrapped in quotes is still valid.
        assert parse_multi_word_terms('"jaleco"') == ["jaleco"]


# ---------------------------------------------------------------------------
# Comma-separated terms (no quotes)
# ---------------------------------------------------------------------------


class TestCommaSeparatedTerms:
    """Commas with no quotes trigger the CSV parsing path."""

    def test_two_unquoted_comma_separated(self):
        assert parse_multi_word_terms("jaleco, avental") == ["jaleco", "avental"]

    def test_three_unquoted_comma_separated(self):
        assert parse_multi_word_terms("jaleco, avental, luva") == ["jaleco", "avental", "luva"]

    def test_comma_without_space(self):
        assert parse_multi_word_terms("jaleco,avental") == ["jaleco", "avental"]

    def test_comma_with_extra_spaces(self):
        assert parse_multi_word_terms("jaleco ,  avental") == ["jaleco", "avental"]

    def test_comma_separated_terms_are_lowercased(self):
        assert parse_multi_word_terms("JALECO, Avental") == ["jaleco", "avental"]

    def test_trailing_comma_produces_no_extra_term(self):
        result = parse_multi_word_terms("jaleco, avental,")
        assert result == ["jaleco", "avental"]

    def test_leading_comma_produces_no_empty_term(self):
        result = parse_multi_word_terms(",jaleco, avental")
        assert result == ["jaleco", "avental"]

    def test_consecutive_commas_produce_no_empty_terms(self):
        result = parse_multi_word_terms("jaleco,,avental")
        assert result == ["jaleco", "avental"]


# ---------------------------------------------------------------------------
# Mixed: quoted + unquoted, comma-separated
# ---------------------------------------------------------------------------


class TestMixedQuotedAndUnquoted:
    """Main use-case from UXD-001: mix of quoted phrases and bare words."""

    def test_quoted_then_unquoted(self):
        assert parse_multi_word_terms('"camisa polo", uniforme') == ["camisa polo", "uniforme"]

    def test_unquoted_then_quoted(self):
        assert parse_multi_word_terms('uniforme, "camisa polo"') == ["uniforme", "camisa polo"]

    def test_two_quoted_one_unquoted(self):
        result = parse_multi_word_terms('"camisa polo", uniforme, "calça social"')
        assert result == ["camisa polo", "uniforme", "calça social"]

    def test_all_quoted_terms(self):
        result = parse_multi_word_terms('"camisa polo", "calça social"')
        assert result == ["camisa polo", "calça social"]

    def test_mixed_case_normalised(self):
        result = parse_multi_word_terms('"Camisa Polo", Uniforme, "Calça Social"')
        assert result == ["camisa polo", "uniforme", "calça social"]

    def test_mixed_with_extra_outer_spaces(self):
        result = parse_multi_word_terms('  "camisa polo" ,  uniforme  ,  "calça social"  ')
        assert result == ["camisa polo", "uniforme", "calça social"]

    def test_three_term_count(self):
        result = parse_multi_word_terms('"camisa polo", uniforme, "calça social"')
        assert len(result) == 3

    def test_quoted_multi_word_is_single_element_not_split(self):
        result = parse_multi_word_terms('"camisa polo", uniforme')
        assert "camisa polo" in result
        # Must NOT have been split on the space.
        assert "camisa" not in result
        assert "polo" not in result

    def test_comma_inside_quotes_is_not_a_delimiter(self):
        result = parse_multi_word_terms('"avental, jaleco"')
        assert result == ["avental, jaleco"]

    def test_empty_quoted_string_is_skipped(self):
        result = parse_multi_word_terms('"", uniforme')
        assert result == ["uniforme"]

    def test_only_empty_quoted_strings_returns_empty(self):
        result = parse_multi_word_terms('"", ""')
        assert result == []


# ---------------------------------------------------------------------------
# Return-type and structural guarantees
# ---------------------------------------------------------------------------


class TestReturnTypeAndStructure:
    """Invariants that hold regardless of which parsing path is taken."""

    def test_returns_list(self):
        assert isinstance(parse_multi_word_terms("jaleco"), list)

    def test_returns_list_for_empty_input(self):
        assert isinstance(parse_multi_word_terms(""), list)

    def test_all_items_are_strings(self):
        result = parse_multi_word_terms('"camisa polo", uniforme, jaleco')
        assert all(isinstance(t, str) for t in result)

    def test_no_item_is_empty_string(self):
        result = parse_multi_word_terms('"camisa polo", uniforme, ,, jaleco')
        assert all(t != "" for t in result)

    def test_all_items_are_lowercase(self):
        result = parse_multi_word_terms('"CAMISA POLO", UNIFORME, Jaleco')
        assert all(t == t.lower() for t in result)

    def test_no_item_has_leading_or_trailing_whitespace(self):
        result = parse_multi_word_terms('  jaleco  ,  "  camisa polo  "  ')
        assert all(t == t.strip() for t in result)
