"""Keyword matching engine for uniform/apparel procurement filtering."""

import re
import unicodedata
from datetime import datetime
from functools import lru_cache
from typing import Optional

import nltk
from nltk.stem import RSLPStemmer

# Ensure RSLP data is available (download only once)
try:
    nltk.data.find("stemmers/rslp")
except LookupError:
    nltk.download("rslp", quiet=True)

_rslp_stemmer = RSLPStemmer()


# Primary keywords for uniform/apparel procurement (PRD Section 4.1)
#
# Strategy: keep ALL clothing-related terms (including ambiguous ones like
# "camisa", "boné", "avental", "colete", "confecção") to avoid false
# negatives, but rely on an extensive KEYWORDS_EXCLUSAO set to filter out
# non-clothing contexts. This ensures we catch "Aquisição de camisas polo
# para guardas" while excluding "confecção de placas de sinalização".
KEYWORDS_UNIFORMES: set[str] = {
    # Primary terms (high precision)
    "uniforme",
    "uniformes",
    "fardamento",
    "fardamentos",
    "farda",
    "fardas",
    # General apparel terms
    "vestuario",
    "vestimenta",
    "vestimentas",
    "indumentaria",
    "roupa",
    "roupas",
    "roupa profissional",
    "vestuario profissional",
    # Textile / manufacturing (ambiguous — guarded by exclusions)
    "confeccao",
    "confeccoes",
    "confeccionado",
    "confeccionados",
    "costura",
    # Specific clothing pieces
    "jaleco",
    "jalecos",
    "guarda-pó",
    "guarda-pós",
    "avental",
    "aventais",
    "colete",
    "coletes",
    "camiseta",
    "camisetas",
    "camisa",
    "camisas",
    "camisa polo",
    "camisas polo",
    "blusa",
    "blusas",
    "calça",
    "calças",
    "bermuda",
    "bermudas",
    "saia",
    "saias",
    "agasalho",
    "agasalhos",
    "jaqueta",
    "jaquetas",
    "macacão",
    "macacoes",
    "jardineira",
    "jardineiras",
    "gandola",
    "gandolas",
    "boné",
    "bonés",
    "meia",
    "meias",
    "bota",
    "botas",
    "sapato",
    "sapatos",
    # Specific contexts
    "uniforme escolar",
    "uniforme hospitalar",
    "uniforme administrativo",
    "uniforme esportivo",
    "uniformes esportivos",
    "uniforme profissional",
    "fardamento militar",
    "fardamento escolar",
    "epi vestuario",
    "epi vestimenta",
    # EPI (Equipamento de Proteção Individual) — often includes apparel
    "epi",
    "epis",
    "equipamento de protecao individual",
    "equipamentos de protecao individual",
    # Common compositions in procurement notices
    "kit uniforme",
    "conjunto uniforme",
    "confeccao de uniforme",
    "confeccao de uniformes",
    "confeccao de camiseta",
    "confeccao de camisetas",
    "aquisição de uniforme",
    "aquisição de uniformes",
    "fornecimento de uniforme",
    "fornecimento de uniformes",
    "aquisição de vestuario",
    "fornecimento de vestuario",
    "aquisição de fardamento",
    "fornecimento de fardamento",
}


# Exclusion keywords (prevent false positives - PRD Section 4.1)
# Matches are checked FIRST; if any exclusion matches, the bid is rejected
# even if a primary keyword also matches.
#
# This list MUST be comprehensive because we keep ambiguous keywords
# (confecção, costura, camisa, colete, avental, boné, bota, meia, etc.)
# to avoid false negatives. Each exclusion blocks a known non-clothing
# context for those ambiguous terms.
KEYWORDS_EXCLUSAO: set[str] = {
    # --- "uniforme/uniformização" in non-clothing context ---
    "uniformizacao",  # standardization — never refers to clothing
    "uniformemente",  # adverb "uniformly" — never refers to clothing
    "uniformização de procedimento",
    "uniformização de entendimento",
    "uniformizacao de jurisprudencia",
    "uniforme de transito",
    "padrao uniforme",
    "padronizacao de uniforme escolar",
    # --- "confecção" in non-clothing context (manufacturing/fabrication) ---
    "confeccao de placa",
    "confeccao de placas",
    "confeccao de grade",
    "confeccao de grades",
    "confeccao de protese",
    "confeccao de proteses",
    "confeccao de merenda",
    "confeccao de materiais graficos",
    "confeccao de material grafico",
    "confeccao de pecas",
    "confeccao de chave",
    "confeccao de chaves",
    "confecção de carimbo",
    "confecção de carimbos",
    "confeccao de letras",
    "confecção de plotagens",
    "confeccao de plotagem",
    "confecção de tampas",
    "confeccao de tampa",
    "confecção de embalagens",
    "confeccao de embalagem",
    "confeccao de mochilas",
    "confeccao e impressao",
    "confeccao e instalacao",
    "confecção e fornecimento de placa",
    "confecção e fornecimento de placas",
    "confeccao de portao",
    "confeccao de portoes",
    "confeccao de pecas de ferro",
    # --- "costura" in non-procurement context (courses/training) ---
    "curso de corte",
    "oficina de corte",
    "aula de corte",
    "instrutor de corte",
    "instrutor de costura",
    "curso de costura",
    "oficina de costura",
    "aula de costura",
    # --- "malha" in non-textile context ---
    "malha viaria",
    "malha rodoviaria",
    "malha tensionada",
    "malha de fibra optica",
    # --- "avental" in non-clothing context ---
    "avental plumbifero",
    # --- "chapéu/boné" in non-clothing context ---
    "chapeu pensador",
    # --- "camisa" in non-clothing context ---
    "amor a camisa",
    # --- "bota" in non-footwear context ---
    "bota de concreto",
    "bota de cimento",
    # --- "meia" in non-clothing context ---
    "meia entrada",
    # --- Software / digital ---
    "software de uniforme",
    "plataforma de uniforme",
    "solucao de software",
    "plataforma web",
    # --- Decoration / events / costumes ---
    "decoracao",
    "fantasia",
    "fantasias",
    "traje oficial",
    "trajes oficiais",
    # --- Non-apparel manufacturing ---
    "tapecaria",
    "forracao",
    # --- "roupa" in non-clothing context (bed/table linens) ---
    "roupa de cama",
    "roupa de mesa",
    "roupa de banho",
    "cama mesa e banho",
    "enxoval hospitalar",
    "enxoval hospital",
    # --- "colete" in non-apparel context ---
    "colete salva vidas",
    "colete salva vida",
    "colete balistico",
    # --- "bota" in non-footwear context (expanded) ---
    "bota de borracha para construcao",
    # --- Construction / infrastructure that matches "bota", "colete" etc. ---
    "material de construcao",
    "materiais de construcao",
    "sinalizacao",
    "sinalizacao visual",
}


# EPI terms that alone (without clothing context) indicate a non-vestuario procurement
EPI_ONLY_KEYWORDS: set[str] = {
    "epi",
    "epis",
    "equipamento de protecao individual",
    "equipamentos de protecao individual",
}


def normalize_text(text: str) -> str:
    """
    Normalize text for keyword matching.

    Normalization steps:
    - Convert to lowercase
    - Remove accents (NFD + remove combining characters)
    - Remove excessive punctuation
    - Normalize whitespace

    Args:
        text: Input text to normalize

    Returns:
        Normalized text (lowercase, no accents, clean whitespace)

    Examples:
        >>> normalize_text("Jáleco Médico")
        'jaleco medico'
        >>> normalize_text("UNIFORME-ESCOLAR!!!")
        'uniforme escolar'
        >>> normalize_text("  múltiplos   espaços  ")
        'multiplos espacos'
    """
    if not text:
        return ""

    # Lowercase
    text = text.lower()

    # Remove accents using NFD normalization
    # NFD = Canonical Decomposition (separates base chars from combining marks)
    text = unicodedata.normalize("NFD", text)
    # Remove combining characters (category "Mn" = Mark, nonspacing)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")

    # Remove punctuation (keep only word characters and spaces)
    # Replace non-alphanumeric with spaces
    text = re.sub(r"[^\w\s]", " ", text)

    # Normalize multiple spaces to single space
    text = re.sub(r"\s+", " ", text)

    return text.strip()


@lru_cache(maxsize=4096)
def stem_word(word: str) -> str:
    """Stem a single normalized word using RSLP (PT-BR stemmer).

    Args:
        word: A single lowercase, accent-free word.

    Returns:
        The stemmed form of the word.
    """
    return _rslp_stemmer.stem(word)


def stem_text(text: str) -> str:
    """Normalize and stem text for improved keyword matching.

    Applies normalize_text() first, then stems each word using RSLP.
    This enables matching inflected forms: "uniformizado" -> "uniform",
    "confeccionado" -> "confeccion", etc.

    Args:
        text: Input text (raw or pre-normalized).

    Returns:
        Normalized and stemmed text with words joined by spaces.

    Examples:
        >>> stem_text("uniformizado")  # same stem as "uniforme"
        >>> stem_text("confeccionado")  # same stem as "confeccao"
    """
    normalized = normalize_text(text)
    if not normalized:
        return ""
    return " ".join(stem_word(w) for w in normalized.split())


def match_keywords(
    objeto: str,
    keywords: set[str],
    exclusions: set[str] | None = None,
    epi_only_keywords: set[str] | None = None,
    keywords_a: set[str] | None = None,
    keywords_b: set[str] | None = None,
    keywords_c: set[str] | None = None,
    threshold: float = 0.6,
) -> tuple[bool, list[str], float]:
    """
    Check if procurement object description contains sector keywords.

    Supports two modes:
    - Binary mode (default): any keyword match approves the item (score=1.0)
    - Tier scoring mode: when keywords_a is provided, uses weighted scoring
      where A=1.0, B=0.7, C=0.3 and score must meet threshold

    Args:
        objeto: Procurement object description (objetoCompra from PNCP API)
        keywords: Set of keywords to search for (flat set, all treated as tier A)
        exclusions: Optional set of exclusion keywords
        epi_only_keywords: Optional set of EPI-only terms for vestuario context check
        keywords_a: Tier A keywords (unambiguous, weight 1.0)
        keywords_b: Tier B keywords (strong, weight 0.7)
        keywords_c: Tier C keywords (ambiguous, weight 0.3)
        threshold: Minimum score to approve (default 0.6)

    Returns:
        Tuple of (approved, matched_keywords, score)
    """
    objeto_norm = normalize_text(objeto)
    objeto_stemmed = stem_text(objeto)

    # Check exclusions first (fail-fast optimization)
    # Exclusions use exact (normalized) matching only — NOT stemming.
    # Stemming on exclusions is too risky: e.g., "uniformizacao" stems to
    # "uniform" which would falsely block ALL uniform-related items.
    if exclusions:
        for exc in exclusions:
            exc_norm = normalize_text(exc)
            pattern = rf"\b{re.escape(exc_norm)}\b"
            if re.search(pattern, objeto_norm):
                return False, [], 0.0

    # Tier scoring mode: use weighted keyword matching
    # Track matched stems to prevent double-counting singular/plural variants
    # (e.g., "bota" and "botas" share stem "bot" — count only once per tier)
    if keywords_a:
        score = 0.0
        matched: list[str] = []
        scored_stems: set = set()
        for kw in keywords_a:
            if _keyword_matches(kw, objeto_norm, objeto_stemmed):
                score = max(score, 1.0)
                matched.append(kw)
        for kw in keywords_b or set():
            if _keyword_matches(kw, objeto_norm, objeto_stemmed):
                score = max(score, 0.7)
                matched.append(kw)
        for kw in keywords_c or set():
            if _keyword_matches(kw, objeto_norm, objeto_stemmed):
                kw_stem = stem_text(kw)
                if kw_stem not in scored_stems:
                    score = min(1.0, score + 0.3)
                    scored_stems.add(kw_stem)
                matched.append(kw)
        return score >= threshold, matched, score

    # Binary mode: any keyword match approves (backward compat)
    matched = []
    for kw in keywords:
        if _keyword_matches(kw, objeto_norm, objeto_stemmed):
            matched.append(kw)

    # EPI-only contextual check
    if epi_only_keywords and matched:
        matched_normalized = {normalize_text(kw) for kw in matched}
        epi_normalized = {normalize_text(kw) for kw in epi_only_keywords}
        if matched_normalized <= epi_normalized:
            return False, [], 0.0

    score = 1.0 if matched else 0.0
    return len(matched) > 0, matched, score


def _keyword_matches(kw: str, objeto_norm: str, objeto_stemmed: str) -> bool:
    """Check if a keyword matches the object text via exact or stemmed match.

    Exact (normalized) match is tried first for precision. Stemmed match
    is used as fallback to catch inflected forms (e.g., "uniformizado"
    matching keyword "uniforme").

    Args:
        kw: Original keyword string.
        objeto_norm: Normalized object text.
        objeto_stemmed: Stemmed object text.

    Returns:
        True if keyword matches via either exact or stemmed match.
    """
    # Exact match (highest priority)
    kw_norm = normalize_text(kw)
    pattern = rf"\b{re.escape(kw_norm)}\b"
    if re.search(pattern, objeto_norm):
        return True
    # Stemmed match (fallback for inflected forms)
    kw_stemmed = stem_text(kw)
    pattern_stemmed = rf"\b{re.escape(kw_stemmed)}\b"
    if re.search(pattern_stemmed, objeto_stemmed):
        return True
    return False


def filter_licitacao(
    licitacao: dict,
    ufs_selecionadas: set[str],
    valor_min: float = 50_000.0,
    valor_max: float = 5_000_000.0,
    keywords: set[str] | None = None,
    exclusions: set[str] | None = None,
    epi_only_keywords: set[str] | None = None,
    keywords_a: set[str] | None = None,
    keywords_b: set[str] | None = None,
    keywords_c: set[str] | None = None,
    threshold: float = 0.6,
) -> tuple[bool, Optional[str], list[str], float]:
    """
    Apply all filters to a single procurement bid (fail-fast sequential filtering).

    Filter order (fastest to slowest for optimization):
    1. UF check (O(1) set lookup)
    2. Value range check (simple numeric comparison)
    3. Keyword matching (regex - most expensive)
    4. Status/deadline validation (datetime parsing)

    Args:
        licitacao: PNCP procurement bid dictionary
        ufs_selecionadas: Set of selected Brazilian state codes (e.g., {'SP', 'RJ'})
        valor_min: Minimum bid value in BRL (default: R$ 50,000)
        valor_max: Maximum bid value in BRL (default: R$ 5,000,000)

    Returns:
        Tuple containing:
        - bool: True if bid passes all filters, False otherwise
        - Optional[str]: Rejection reason if rejected, None if approved
        - List[str]: Matched keywords (empty if rejected)
        - float: Relevance score (0.0 if rejected)

    Examples:
        >>> bid = {
        ...     "uf": "SP",
        ...     "valorTotalEstimado": 150000.0,
        ...     "objetoCompra": "Aquisição de uniformes escolares",
        ...     "dataAberturaProposta": "2026-12-31T10:00:00Z"
        ... }
        >>> filter_licitacao(bid, {"SP"})
        (True, None, ['uniforme'], 1.0)

        >>> bid_rejected = {"uf": "RJ", "valorTotalEstimado": 100000.0}
        >>> filter_licitacao(bid_rejected, {"SP"})
        (False, "UF 'RJ' não selecionada", [], 0.0)
    """
    # 1. UF Filter (fastest check)
    uf = licitacao.get("uf", "")
    if uf not in ufs_selecionadas:
        return False, f"UF '{uf}' não selecionada", [], 0.0

    # 2. Value Range Filter
    # Support both PNCP field name and NormalizedRecord field name
    valor = licitacao.get("valorTotalEstimado")
    if valor is None:
        valor = licitacao.get("valor_estimado")

    # Many PNCP items (especially "Registro de Preços") have valor=0.0 or null
    # because the estimated value is determined during bidding. These are
    # legitimate procurement items — skip the value check for them.
    if valor is not None and valor > 0:
        if not (valor_min <= valor <= valor_max):
            return False, f"Valor R$ {valor:,.2f} fora da faixa", [], 0.0

    # 3. Keyword Filter (most expensive - regex matching)
    kw = keywords if keywords is not None else KEYWORDS_UNIFORMES
    exc = exclusions if exclusions is not None else KEYWORDS_EXCLUSAO
    # Support both PNCP field name and NormalizedRecord field name
    objeto = licitacao.get("objetoCompra") or licitacao.get("objeto", "")
    match, keywords_found, kw_score = match_keywords(
        objeto,
        kw,
        exc,
        epi_only_keywords=epi_only_keywords,
        keywords_a=keywords_a,
        keywords_b=keywords_b,
        keywords_c=keywords_c,
        threshold=threshold,
    )

    if not match:
        return False, "Não contém keywords do setor", [], 0.0

    # 4. Deadline Filter (TD-M01) — uses dataFimReceberPropostas
    # The field dataAberturaProposta is the proposal OPENING date (not deadline).
    # We use dataFimReceberPropostas (when available) to exclude bids whose
    # submission deadline has already passed, filtering out historical bids
    # that are no longer actionable.
    data_fim_str = licitacao.get("dataFimReceberPropostas")
    if data_fim_str:
        try:
            # Handle both "Z" suffix and "+00:00" offset
            data_fim = datetime.fromisoformat(data_fim_str.replace("Z", "+00:00"))
            from datetime import timezone

            now = datetime.now(timezone.utc)
            if data_fim < now:
                return False, "Prazo de submissão encerrado", [], 0.0
        except (ValueError, TypeError):
            pass  # Unparseable date — don't reject, let it through

    return True, None, keywords_found, kw_score


def filter_batch(
    licitacoes: list[dict],
    ufs_selecionadas: set[str],
    valor_min: float = 50_000.0,
    valor_max: float = 5_000_000.0,
    keywords: set[str] | None = None,
    exclusions: set[str] | None = None,
    epi_only_keywords: set[str] | None = None,
    keywords_a: set[str] | None = None,
    keywords_b: set[str] | None = None,
    keywords_c: set[str] | None = None,
    threshold: float = 0.6,
) -> tuple[list[dict], dict[str, int]]:
    """
    Filter a batch of procurement bids and return statistics.

    Applies filter_licitacao() to each bid and tracks rejection reasons
    for observability and debugging.

    Args:
        licitacoes: List of PNCP procurement bid dictionaries
        ufs_selecionadas: Set of selected Brazilian state codes
        valor_min: Minimum bid value in BRL (default: R$ 50,000)
        valor_max: Maximum bid value in BRL (default: R$ 5,000,000)

    Returns:
        Tuple containing:
        - List[dict]: Approved bids (passed all filters)
        - Dict[str, int]: Statistics dictionary with rejection counts

    Statistics Keys:
        - total: Total number of bids processed
        - aprovadas: Number of bids that passed all filters
        - rejeitadas_uf: Rejected due to UF not selected
        - rejeitadas_valor: Rejected due to value outside range
        - rejeitadas_keyword: Rejected due to missing uniform keywords
        - rejeitadas_prazo: Rejected due to deadline passed
        - rejeitadas_outros: Rejected for other reasons

    Examples:
        >>> bids = [
        ...     {"uf": "SP", "valorTotalEstimado": 100000, "objetoCompra": "Uniformes"},
        ...     {"uf": "RJ", "valorTotalEstimado": 100000, "objetoCompra": "Uniformes"}
        ... ]
        >>> aprovadas, stats = filter_batch(bids, {"SP"})
        >>> stats["total"]
        2
        >>> stats["aprovadas"]
        1
        >>> stats["rejeitadas_uf"]
        1
    """
    aprovadas: list[dict] = []
    stats: dict[str, int] = {
        "total": len(licitacoes),
        "aprovadas": 0,
        "rejeitadas_uf": 0,
        "rejeitadas_valor": 0,
        "rejeitadas_keyword": 0,
        "rejeitadas_prazo": 0,
        "rejeitadas_outros": 0,
    }

    for lic in licitacoes:
        aprovada, motivo, kw_found, kw_score = filter_licitacao(
            lic,
            ufs_selecionadas,
            valor_min,
            valor_max,
            keywords,
            exclusions,
            epi_only_keywords,
            keywords_a,
            keywords_b,
            keywords_c,
            threshold,
        )

        if aprovada:
            lic["matched_keywords"] = kw_found
            lic["relevance_score"] = round(kw_score, 2)
            aprovadas.append(lic)
            stats["aprovadas"] += 1
        else:
            # Categorize rejection reason for statistics
            motivo_lower = (motivo or "").lower()
            if "uf" in motivo_lower and "não selecionada" in motivo_lower:
                stats["rejeitadas_uf"] += 1
            elif "valor" in motivo_lower and "fora da faixa" in motivo_lower:
                stats["rejeitadas_valor"] += 1
            elif "keyword" in motivo_lower:
                stats["rejeitadas_keyword"] += 1
            elif "prazo" in motivo_lower:
                stats["rejeitadas_prazo"] += 1
            else:
                stats["rejeitadas_outros"] += 1

    return aprovadas, stats
