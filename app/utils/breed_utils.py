from __future__ import annotations

import re
from typing import List, Optional


def normalize_breed_key(name: Optional[str]) -> str:
    """
    Normalizes a breed string to maximize matching with normalized BREED_GROUPS keys.

    - Lowercases
    - Removes the word "mix" and variations
    - Splits on common separators (/, &, -, ,) and uses the first token (for single-key use)
    - Collapses extra whitespace

    NOTE: For cases where you want to consider multiple tokens (e.g., "A/B"), use
    split_breed_tokens() instead. This function is optimized for a single-key lookup.
    """
    if not name:
        return ""
    s = name.strip().lower()

    # remove common "mix" patterns
    s = re.sub(r"\bmix\b", "", s)
    s = re.sub(r"\b/mix\b", "", s)

    # split multi-breeds and pick the first token
    for sep in ["/", "&", "-", ","]:
        if sep in s:
            s = s.split(sep)[0]

    # collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def split_breed_tokens(name: Optional[str]) -> List[str]:
    """
    Split a breed string like "Australian Shepherd/Dalmatian" or "Pug Mix"
    into candidate token keys for matching.

    Returns a list of tokens with the FULL normalized key first, followed by
    component tokens. Duplicates are removed while preserving order.
    """
    if not name:
        return []

    s = name.strip()
    # Include the full normalized key
    full = normalize_breed_key(s)

    lowered = s.lower()
    # Remove "mix" tokens for component extraction
    lowered = re.sub(r"\bmix\b", "", lowered)
    parts = re.split(r"[\/&,\-]", lowered)

    tokens: List[str] = []
    for part in parts:
        norm = normalize_breed_key(part)
        if norm:
            tokens.append(norm)

    # De-duplicate while preserving order; full key first
    seen = set()
    out: List[str] = []
    for t in [full] + tokens:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


__all__ = ["normalize_breed_key", "split_breed_tokens"]