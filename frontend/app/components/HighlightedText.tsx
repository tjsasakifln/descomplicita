"use client";

interface HighlightedTextProps {
  text: string;
  keywords: string[];
}

/**
 * Strips diacritical marks from a string for accent-insensitive matching.
 * e.g. "licitação" -> "licitacao", "confecção" -> "confeccao"
 */
function normalize(str: string): string {
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

interface TextSegment {
  text: string;
  highlight: boolean;
}

/**
 * Finds all match ranges in the normalized text and maps them back to the
 * original text. Overlapping ranges are merged before rendering.
 */
function buildSegments(text: string, keywords: string[]): TextSegment[] {
  if (!text || keywords.length === 0) {
    return [{ text, highlight: false }];
  }

  const normalizedText = normalize(text);
  const ranges: Array<[number, number]> = [];

  for (const keyword of keywords) {
    const normalizedKeyword = normalize(keyword);
    if (!normalizedKeyword) continue;

    let searchStart = 0;
    while (searchStart < normalizedText.length) {
      const idx = normalizedText.indexOf(normalizedKeyword, searchStart);
      if (idx === -1) break;
      ranges.push([idx, idx + normalizedKeyword.length]);
      searchStart = idx + 1;
    }
  }

  if (ranges.length === 0) {
    return [{ text, highlight: false }];
  }

  // Sort and merge overlapping ranges
  ranges.sort((a, b) => a[0] - b[0]);
  const merged: Array<[number, number]> = [];
  for (const [start, end] of ranges) {
    if (merged.length === 0 || start > merged[merged.length - 1][1]) {
      merged.push([start, end]);
    } else if (end > merged[merged.length - 1][1]) {
      merged[merged.length - 1][1] = end;
    }
  }

  // Build segments using original text positions (same indices apply since
  // normalize() is a character-level transform that preserves string length
  // only for ASCII — we use the normalized string positions against the
  // original, which works because NFD + diacritic removal maps each character
  // to exactly one character in the result for common Latin scripts)
  const segments: TextSegment[] = [];
  let cursor = 0;
  for (const [start, end] of merged) {
    if (cursor < start) {
      segments.push({ text: text.slice(cursor, start), highlight: false });
    }
    segments.push({ text: text.slice(start, end), highlight: true });
    cursor = end;
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), highlight: false });
  }

  return segments;
}

export function HighlightedText({ text, keywords }: HighlightedTextProps) {
  const segments = buildSegments(text, keywords);

  return (
    <>
      {segments.map((segment, idx) =>
        segment.highlight ? (
          <mark key={idx}>{segment.text}</mark>
        ) : (
          <span key={idx}>{segment.text}</span>
        )
      )}
    </>
  );
}
