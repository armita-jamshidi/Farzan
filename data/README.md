# data/

Scripts that build the Rumi Persian-English parallel dataset, one row per bayt (couplet).

| Step | Script | Output |
|---|---|---|
| 1. Persian text + metre | `extract_ganjoor.py` | `interim/persian.jsonl` (60,239 couplets) |
| 2. English translations | `fetch_translations.py` | `raw/<source>.txt`, `interim/english/<source>.jsonl` |
| 3. Verse alignment | `align.py` (LaBSE + monotonic DP) | `interim/aligned/<source>.jsonl` |
| 4. Splits | `make_splits.py` | `processed/{train,validation,test}.jsonl` |
| 5. Publish | `push_to_hub.py` | Hub dataset + `DATASET_CARD.md` |

Every source and its licensing status is listed in `sources.py`. Only sources
marked `ok` are used.

```bash
git clone --depth 1 https://github.com/ganjoor/ganjoor-data /tmp/ganjoor-data
python data/extract_ganjoor.py --ganjoor /tmp/ganjoor-data
python data/fetch_translations.py          # downloads OCR text, checks title pages
for s in nicholson_mathnawi_1_2 nicholson_mathnawi_3_4 whinfield_masnavi redhouse_mesnevi_1881 nicholson_divan_1898; do
  python data/align.py --persian data/interim/persian.jsonl \
    --english data/interim/english/$s.jsonl --out data/interim/aligned/$s.jsonl
done
python data/make_splits.py --aligned data/interim/aligned/*.jsonl
```

LaBSE vectors are cached in `interim/labse_cache.sqlite`. The first run embeds
about 120k sentences and takes roughly an hour on a 4-core CPU; later runs take
about a minute.

## Scans used

Each scan's title page is checked by `fetch_translations.py` before parsing.

| Source | Internet Archive scan | Title page says |
|---|---|---|
| Whinfield, Masnavi (abridged), 2nd ed. | `masnaviimanavisp00jala_0` | Trübner, London, 1898, "Second Edition" |
| Nicholson, Mathnawi vol. II (Books 1-2) | `in.ernet.dli.2015.70297` | Gibb Memorial, Luzac, 1926 |
| Nicholson, Mathnawi vol. IV (Books 3-4) | `in.ernet.dli.2015.70298` | Gibb Memorial, Luzac, 1930 |
| Nicholson, Selected Poems from the Divani Shamsi Tabriz | `india.history.resource.111025` | Cambridge University Press, 1898 |
| Redhouse, The Mesnevi, Book 1 | `in.ernet.dli.2015.55252` | Trübner (no date on this copy; preface signed 1880, published 1881) |

Not used: the archive's copy `mathnawiofjalalu0006unse` is Nicholson vol. VI
(Books 5-6), a 1977 reprint, and Books 5-6 wait on a licensing decision.
Google-scanned copies of Redhouse were skipped because Google attaches a
non-commercial usage request to them.

## Results (first full run)

| Source | Aligned rows | English units used | Median LaBSE score | Check |
|---|---|---|---|---|
| Nicholson Mathnawi Books 1-2 | 7,345 of 7,832 couplets | 90% | 0.56 | 99.9% verse-number agreement |
| Nicholson Mathnawi Books 3-4 | 8,135 of 8,660 couplets | 87% | 0.56 | 99.8% verse-number agreement |
| Whinfield (abridged, Books 1-6) | 2,249 | 73% | 0.56 | spot-check |
| Redhouse Book 1 | 1,587 | 51% | 0.50 | spot-check |
| Nicholson Divan (48 ghazals) | 387 | 80% | 0.63 | all 48 ghazals found in Ganjoor |

"Verse-number agreement": Nicholson prints a verse number every five verses.
For each aligned row we compare Ganjoor's verse number with Nicholson's; in a
correct alignment the difference stays nearly constant, so a row whose
difference jumps away from its neighbours' is a likely error.

A hand spot-check of 30 random rows found Nicholson's Mathnawi rows 12 of 12
correct and the Divan 5 of 6. Whinfield and Redhouse rows are usually in the
right place but often hold only half of the couplet or one extra half-line,
because those translations print each half-line separately and Whinfield
paraphrases freely. Single short lines are now dropped, which removes most
half-couplets. Use `translation_style` to filter when training.

## Row schema

| field | example |
|---|---|
| `id` | `masnavi-1-1-1` |
| `source` | `Masnavi` or `Divan` |
| `book` | Masnavi daftar 1-6 (null for the Divan) |
| `poem_number` | Ganjoor section number (Masnavi) or Foruzanfar ghazal number (Divan) |
| `verse_number` | couplet number within the book (Masnavi) or within the ghazal (Divan) |
| `hemistich_1`, `hemistich_2`, `persian_text` | the two half-lines, and both joined with ` / ` |
| `english_text` | public-domain translation of the couplet |
| `meter_name` | Ganjoor metre label, e.g. `فاعلاتن فاعلاتن فاعلن (رمل مسدس محذوف یا وزن مثنوی)` |
| `translator`, `license_note` | who translated it and why it is public domain |
| `align_score`, `align_type` | LaBSE similarity and bead shape (`1:1`, `2:1`, ...) |
