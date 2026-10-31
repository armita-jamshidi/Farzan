# data/

Scripts that build the Rumi Persian-English parallel dataset, one row per bayt (couplet).

| Step | Script | Output |
|---|---|---|
| 1. Persian text + metre | `extract_ganjoor.py` | `interim/persian.jsonl` (60,239 couplets) |
| 2. English translations | `fetch_translations.py` (next) | `interim/english/<source>.jsonl` |
| 3. Verse alignment | `align.py` (LaBSE + monotonic DP) | `interim/aligned/<source>.jsonl` |
| 4. Splits | `make_splits.py` | `processed/{train,validation,test}.jsonl` |
| 5. Publish | `push_to_hub.py` | Hub dataset + `DATASET_CARD.md` |

Every source and its licensing status is listed in `sources.py`. Only sources
marked `ok` are used.

```bash
git clone --depth 1 https://github.com/ganjoor/ganjoor-data /tmp/ganjoor-data
python data/extract_ganjoor.py --ganjoor /tmp/ganjoor-data
```

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
