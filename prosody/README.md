# prosody/

- `normalize.py`: Persian text normalization (Arabic/Persian ye and kaf, diacritics, ZWNJ, digits) used for WER and data cleaning.
- `meters.py`: classical metres ('aruz) as long (`-`) / short (`u`) syllable patterns, parsed from Ganjoor's metre labels. Covers 98.5% of Rumi's couplets; the rest have no label or a rare foot and need a manual check.

Scansion of individual verses and rhythm scoring come in milestone 5.
