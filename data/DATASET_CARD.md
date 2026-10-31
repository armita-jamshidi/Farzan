---
language: [fa, en]
license: other
task_categories: [translation]
pretty_name: Rumi Persian-English Couplets
size_categories: [10K<n<100K]
---

# Rumi Persian-English Couplets

One row per bayt (couplet) of Rumi's Masnavi-ye Ma'navi and Divan-e Shams,
with the Persian text, its classical metre, and an English translation from a
public-domain edition, aligned verse by verse.

## Sources

- **Persian text and metre labels**: [Ganjoor](https://ganjoor.net), via
  [ganjoor/ganjoor-data](https://github.com/ganjoor/ganjoor-data). Rumi's text is
  public domain; the digitization is Ganjoor's work and is credited here.
- **English**: only translations that are public domain in both the US and the
  UK/EU. Each row's `translator` and `license_note` say which edition it came from.

## Splits

Splits are made by passage (a Masnavi section or a Divan ghazal), so no passage
is split between train and test. The test split is held out and never used for
training.

<!-- counts and alignment quality filled in by data/make_splits.py output -->

## Limitations

- English rows were aligned automatically with LaBSE embeddings. `align_score`
  is the similarity; low-scoring rows are dropped, but some misalignments remain.
- Older translations are often paraphrastic (Whinfield abridges heavily), so
  BLEU against them is a rough signal for poetry.
- Metre labels come from Ganjoor without correction.
