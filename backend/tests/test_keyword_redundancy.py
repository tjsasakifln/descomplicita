"""
RT1/A7: Keyword redundancy detection test.

Asserts that no keyword set in filter.py or sectors.py contains entries
that are redundant under normalize_text() — i.e., two different original
strings that normalize to the same value.
"""

from collections import defaultdict

import pytest

from filter import KEYWORDS_EXCLUSAO, KEYWORDS_UNIFORMES, normalize_text
from sectors import SECTORS


def _find_redundancies(kw_set: set) -> dict:
    """Return a dict of {normalized: [originals]} where len(originals) > 1."""
    norm_map = defaultdict(list)
    for kw in sorted(kw_set):
        norm_map[normalize_text(kw)].append(kw)
    return {n: g for n, g in norm_map.items() if len(g) > 1}


class TestKeywordRedundancy:
    """Ensure no keyword set has normalization-redundant entries."""

    def test_keywords_uniformes_no_redundancy(self):
        dupes = _find_redundancies(KEYWORDS_UNIFORMES)
        assert dupes == {}, f"KEYWORDS_UNIFORMES redundancies: {dupes}"

    def test_keywords_exclusao_no_redundancy(self):
        dupes = _find_redundancies(KEYWORDS_EXCLUSAO)
        assert dupes == {}, f"KEYWORDS_EXCLUSAO redundancies: {dupes}"

    @pytest.mark.parametrize("sector_id", list(SECTORS.keys()))
    def test_sector_keywords_no_redundancy(self, sector_id):
        cfg = SECTORS[sector_id]
        dupes = _find_redundancies(cfg.keywords)
        assert dupes == {}, f"{sector_id}.keywords redundancies: {dupes}"

    @pytest.mark.parametrize("sector_id", list(SECTORS.keys()))
    def test_sector_keywords_a_no_redundancy(self, sector_id):
        cfg = SECTORS[sector_id]
        if not cfg.keywords_a:
            pytest.skip("No keywords_a for this sector")
        dupes = _find_redundancies(cfg.keywords_a)
        assert dupes == {}, f"{sector_id}.keywords_a redundancies: {dupes}"

    @pytest.mark.parametrize("sector_id", list(SECTORS.keys()))
    def test_sector_keywords_b_no_redundancy(self, sector_id):
        cfg = SECTORS[sector_id]
        if not cfg.keywords_b:
            pytest.skip("No keywords_b for this sector")
        dupes = _find_redundancies(cfg.keywords_b)
        assert dupes == {}, f"{sector_id}.keywords_b redundancies: {dupes}"

    @pytest.mark.parametrize("sector_id", list(SECTORS.keys()))
    def test_sector_keywords_c_no_redundancy(self, sector_id):
        cfg = SECTORS[sector_id]
        if not cfg.keywords_c:
            pytest.skip("No keywords_c for this sector")
        dupes = _find_redundancies(cfg.keywords_c)
        assert dupes == {}, f"{sector_id}.keywords_c redundancies: {dupes}"

    @pytest.mark.parametrize("sector_id", list(SECTORS.keys()))
    def test_sector_exclusions_no_redundancy(self, sector_id):
        cfg = SECTORS[sector_id]
        if not cfg.exclusions:
            pytest.skip("No exclusions for this sector")
        dupes = _find_redundancies(cfg.exclusions)
        assert dupes == {}, f"{sector_id}.exclusions redundancies: {dupes}"
