"""Classical Persian metres ('aruz) as long/short syllable patterns.

Notation: "-" is a long syllable, "u" a short one. Patterns are for one
hemistich (mesra'). They are the canonical forms; common licences (for example
a first foot fa'ilatun in place of fa'alatun, or an over-long final syllable)
are handled by the scorer, not here.
"""

from __future__ import annotations

import re

FEET: dict[str, str] = {
    "فاعلاتن": "-u--",
    "فاعلات": "-u-u",
    "فاعلن": "-u-",
    "فعلاتن": "uu--",
    "فعلات": "uu-u",
    "فعلن": "uu-",
    "فعل": "u-",
    "فع": "-",
    "مفاعیلن": "u---",
    "مفاعیل": "u--u",
    "مفاعلن": "u-u-",
    "فعولن": "u--",
    "فعول": "u-u",
    "مفعولن": "---",
    "مفعول": "--u",
    "مستفعلن": "--u-",
    "مفتعلن": "-uu-",
    "متفاعلن": "uu-u-",
    "متفاعلاتن": "uu-u--",
}

_PAREN = re.compile(r"\(.*?\)")


def split_metre_label(label: str) -> tuple[list[str], str]:
    """Split a Ganjoor metre label into (feet, name).

    "فاعلاتن فاعلاتن فاعلن (رمل مسدس محذوف یا وزن مثنوی)"
    -> (["فاعلاتن", "فاعلاتن", "فاعلن"], "رمل مسدس محذوف یا وزن مثنوی")
    """
    name = _PAREN.search(label)
    feet = _PAREN.sub("", label).split()
    return feet, (name.group(0)[1:-1].strip() if name else "")


def metre_pattern(label: str) -> str | None:
    """Long/short pattern for one hemistich, or None if a foot is unknown."""
    feet, _ = split_metre_label(label)
    if not feet or any(f not in FEET for f in feet):
        return None
    return "".join(FEET[f] for f in feet)


# The Masnavi's metre, for reference: ramal musaddas mahzuf.
MASNAVI_METRE = "فاعلاتن فاعلاتن فاعلن (رمل مسدس محذوف یا وزن مثنوی)"
