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

| split | rows | unique couplets |
|---|---|---|
| train | 16,749 | 14,063 |
| validation | 1,315 | 1,132 |
| test | 1,639 | 1,355 |

A couplet can have more than one row when several translators cover it
(Masnavi Book 1 has Nicholson, Whinfield and Redhouse). All rows for a passage
are in the same split. The test split always contains the Song of the Reed
(Masnavi 1:1-18).

| translator | edition | style | rows |
|---|---|---|---|
| R. A. Nicholson | Mathnawi vols. II and IV, 1926 and 1930 (Books 1-4) | literal prose | 15,480 |
| R. A. Nicholson | Selected Poems from the Divani Shamsi Tabriz, 1898 | close prose | 387 |
| E. H. Whinfield | Masnavi i Ma'navi, abridged, 2nd ed. 1898 | free paraphrase | 2,249 |
| J. W. Redhouse | The Mesnevi, Book 1, 1881 | rhymed verse | 1,587 |

Alignment quality: for Nicholson's Mathnawi, 99.8-99.9% of rows agree with
Nicholson's own printed verse numbers. A hand check of 30 random rows found the
literal Nicholson rows almost always right; Whinfield and Redhouse rows are
looser and sometimes hold half a couplet or an extra half-line. For
translation training and evaluation, `translation_style` lets you keep only the
literal sources.

## Limitations

- English rows were aligned automatically with LaBSE embeddings. `align_score`
  is the similarity. `align_kept_by` is `score` for confident rows and
  `context` for weaker rows kept because confident neighbours box them in.
- The English comes from OCR of old scans, so some typos remain
  ("donkev", "w'ho").
- Older translations are often paraphrastic (Whinfield abridges heavily), so
  BLEU against them is a rough signal for poetry.
- Metre labels come from Ganjoor without correction.
