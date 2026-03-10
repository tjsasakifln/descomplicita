#!/usr/bin/env python3
"""
CI script: detect redundant accent/normalization variants in keyword sets.

Scans all keyword sets in filter.py and sectors.py, computes normalize_text()
for every keyword, and reports any pairs where two different keywords normalize
to the same string. Exits with code 1 if redundancies are found.

Usage:
    python scripts/check_keyword_redundancy.py
"""
import sys
import os
from collections import defaultdict

# Ensure backend/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from filter import KEYWORDS_UNIFORMES, KEYWORDS_EXCLUSAO, normalize_text
from sectors import SECTORS


def check_set(name: str, kw_set: set) -> list:
    """Check a keyword set for normalization-redundant entries.

    Returns a list of (normalized_form, [original1, original2, ...]) tuples
    where multiple originals normalize to the same string.
    """
    norm_map = defaultdict(list)
    for kw in sorted(kw_set):
        norm_map[normalize_text(kw)].append(kw)

    redundancies = []
    for norm, originals in sorted(norm_map.items()):
        if len(originals) > 1:
            redundancies.append((norm, originals))
    return redundancies


def main() -> int:
    all_sets = {
        "filter.KEYWORDS_UNIFORMES": KEYWORDS_UNIFORMES,
        "filter.KEYWORDS_EXCLUSAO": KEYWORDS_EXCLUSAO,
    }

    for sector_id, cfg in SECTORS.items():
        all_sets[f"sectors.{sector_id}.keywords"] = cfg.keywords
        if cfg.keywords_a:
            all_sets[f"sectors.{sector_id}.keywords_a"] = cfg.keywords_a
        if cfg.keywords_b:
            all_sets[f"sectors.{sector_id}.keywords_b"] = cfg.keywords_b
        if cfg.keywords_c:
            all_sets[f"sectors.{sector_id}.keywords_c"] = cfg.keywords_c
        if cfg.exclusions:
            all_sets[f"sectors.{sector_id}.exclusions"] = cfg.exclusions

    total_redundancies = 0
    for name, kw_set in sorted(all_sets.items()):
        redundancies = check_set(name, kw_set)
        if redundancies:
            print(f"REDUNDANCY in {name}:")
            for norm, originals in redundancies:
                print(f"  normalize to '{norm}': {originals}")
            total_redundancies += len(redundancies)
        else:
            print(f"  OK {name} ({len(kw_set)} keywords)")

    print()
    if total_redundancies > 0:
        print(f"FAILED: {total_redundancies} redundant keyword group(s) found.")
        print("Remove accented duplicates — normalize_text() handles accent stripping.")
        return 1
    else:
        print(f"PASSED: No redundancies found across {len(all_sets)} keyword sets.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
