"""Persian text normalization shared by the dataset, evaluation and the practice coach."""

from __future__ import annotations

import re
import unicodedata

ZWNJ = "‌"

# Arabic code points that have a Persian equivalent
_CHAR_MAP = str.maketrans(
    {
        "ي": "ی",  # ARABIC YEH -> FARSI YEH
        "ى": "ی",  # ALEF MAKSURA -> FARSI YEH
        "ك": "ک",  # ARABIC KAF -> KEHEH
        "ۀ": "ه",  # HEH WITH YEH ABOVE (ۀ) -> HEH
        "ة": "ه",  # TEH MARBUTA -> HEH
        "أ": "ا",  # ALEF WITH HAMZA ABOVE -> ALEF
        "إ": "ا",  # ALEF WITH HAMZA BELOW -> ALEF
        "ٱ": "ا",  # ALEF WASLA -> ALEF
        **{chr(0x06F0 + i): str(i) for i in range(10)},  # Persian digits
        **{chr(0x0660 + i): str(i) for i in range(10)},  # Arabic-Indic digits
    }
)

# Harakat, tanwin, shadda, sukun, superscript alef, hamza above/below, tatweel
_DIACRITICS = re.compile(r"[ً-ٰٟـ]")
_PUNCT = re.compile(r"[^\w\s‌]")
_SPACES = re.compile(r"\s+")


def normalize(text: str, *, zwnj: str = "remove", strip_punct: bool = True) -> str:
    """Normalize Persian text for comparison.

    zwnj: what to do with zero-width non-joiners: "remove" joins the parts
    (می‌کند -> میکند), "space" splits them (-> می کند), "keep" leaves them.
    Recognizers disagree about ZWNJ, so "remove" is the default for scoring.
    """
    text = unicodedata.normalize("NFC", text)
    text = unicodedata.normalize("NFKC", text)  # presentation forms (ﻻ, ﮐ ...) -> base letters
    text = text.translate(_CHAR_MAP)
    text = _DIACRITICS.sub("", text)
    if zwnj == "remove":
        text = text.replace(ZWNJ, "")
    elif zwnj == "space":
        text = text.replace(ZWNJ, " ")
    if strip_punct:
        text = _PUNCT.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def tokenize(text: str) -> list[str]:
    """Normalize, then split into words."""
    return normalize(text).split()
