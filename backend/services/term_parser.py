"""Multi-word term parsing (UXD-001)."""

import csv
import io


def parse_multi_word_terms(raw: str) -> list[str]:
    """Parse search terms supporting quoted multi-word phrases and comma delimiters.

    Supports:
    - Quoted terms: "camisa polo" -> camisa polo
    - Comma-separated: "camisa polo", uniforme -> [camisa polo, uniforme]
    - Mixed: "camisa polo", uniforme, "calca social" -> 3 terms
    - Simple space-separated (backward compat): jaleco avental -> [jaleco, avental]

    Args:
        raw: Raw search terms string from user input.

    Returns:
        List of parsed terms (lowercase, stripped).
    """
    if not raw or not raw.strip():
        return []

    raw = raw.strip()

    # If input contains quotes or commas, use CSV-style parsing
    if '"' in raw or "," in raw:
        terms = []
        reader = csv.reader(io.StringIO(raw), skipinitialspace=True)
        for row in reader:
            for term in row:
                cleaned = term.strip().lower()
                if cleaned:
                    terms.append(cleaned)
        return terms

    # Fallback: space-separated (backward compatibility)
    return [t.strip().lower() for t in raw.split() if t.strip()]
