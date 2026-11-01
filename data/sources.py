"""Registry of text sources and their licensing status.

status:
  "ok"      public domain in both the US and the UK/EU, cleared for training and the Hub
  "ask"     unclear or split status, waiting on the project owner's decision
  "exclude" under copyright, never used
Downloads happen in data/fetch_translations.py; the URL for each source is
checked against the scanned title page (edition and year) before use.
"""

SOURCES = {
    "ganjoor": {
        "what": "Persian text of the Masnavi (6 books) and Divan-e Shams ghazals, with metre labels",
        "where": "https://github.com/ganjoor/ganjoor-data",
        "author_died": 1273,
        "status": "ask",
        "license_note": (
            "Rumi's text (13th c.) is public domain. The ganjoor-data repo has no LICENSE file; "
            "Ganjoor's software is GPL, and Hub mirrors label the data GPL-2.0 or CC BY 4.0 "
            "inconsistently. We keep only verse text and metre labels and credit Ganjoor."
        ),
    },
    "whinfield_masnavi": {
        "what": "E. H. Whinfield, Masnavi i Ma'navi (abridged), 1887; 2nd ed. 1898",
        "translator": "E. H. Whinfield",
        "published": 1898,
        "author_died": 1922,
        "style": "abridged, free verse paraphrase",
        "status": "ok",
        "license_note": "Public domain: published 1898 (US) and translator died 1922 (UK/EU life+70).",
    },
    "nicholson_mathnawi_1_2": {
        "what": "R. A. Nicholson, The Mathnawi of Jalalu'ddin Rumi, Vol. II (translation of Books I-II), 1926",
        "translator": "R. A. Nicholson",
        "published": 1926,
        "author_died": 1945,
        "books": [1, 2],
        "style": "literal prose, one paragraph per couplet",
        "status": "ok",
        "license_note": "Public domain: published 1926 (US, pre-1931) and translator died 1945 (UK/EU life+70 ended 2015).",
    },
    "nicholson_mathnawi_3_4": {
        "what": "R. A. Nicholson, The Mathnawi of Jalalu'ddin Rumi, Vol. IV (translation of Books III-IV), 1930",
        "translator": "R. A. Nicholson",
        "published": 1930,
        "author_died": 1945,
        "books": [3, 4],
        "style": "literal prose, one paragraph per couplet",
        "status": "ok",
        "license_note": "Public domain: published 1930 (US PD since 1 Jan 2026) and translator died 1945 (UK/EU).",
    },
    "nicholson_mathnawi_5_6": {
        "what": "R. A. Nicholson, The Mathnawi of Jalalu'ddin Rumi, Vol. VI (translation of Books V-VI), 1934",
        "translator": "R. A. Nicholson",
        "published": 1934,
        "author_died": 1945,
        "books": [5, 6],
        "style": "literal prose, one paragraph per couplet",
        "status": "ask",
        "license_note": (
            "Public domain in the UK/EU (translator died 1945) but still under US copyright "
            "until 1 Jan 2030 (published 1934, 95-year term)."
        ),
    },
    "nicholson_divan_1898": {
        "what": "R. A. Nicholson, Selected Poems from the Divani Shamsi Tabriz, 1898 (48 ghazals, Persian + English)",
        "translator": "R. A. Nicholson",
        "published": 1898,
        "author_died": 1945,
        "style": "close line-by-line prose",
        "status": "ok",
        "license_note": "Public domain: published 1898 (US) and translator died 1945 (UK/EU).",
    },
    "redhouse_mesnevi_1881": {
        "what": "J. W. Redhouse, The Mesnevi (Book I), 1881, rhymed verse",
        "translator": "J. W. Redhouse",
        "published": 1881,
        "author_died": 1892,
        "style": "rhymed verse, loose",
        "status": "ok",
        "license_note": "Public domain: published 1881, translator died 1892.",
    },
    # Never used: modern translations still under copyright.
    "excluded": {
        "what": "Coleman Barks, A. J. Arberry (1949-), Kabir Helminski, Jawid Mojaddedi, Alan Williams, Franklin Lewis",
        "status": "exclude",
        "license_note": "Under copyright. Not downloaded, not used for training, not in the repo.",
    },
}
