# Farzan: a Rumi reader and recitation coach

Farzan is a Rumi companion built on the Hugging Face ecosystem. It will:

1. **Listen**: recite a Rumi poem aloud in Persian, with correct pronunciation and metre.
2. **Translate**: turn a Persian couplet into faithful English, with a short explanation.
3. **Practice**: listen to you recite, check the words, and give feedback on rhythm and metre.

> Status: milestone 1 (dataset) in progress. Links to the Space, model and
> dataset will be added as they are published.

## Repository layout

| folder | what it holds |
|---|---|
| `data/` | collect, clean, align and publish the Persian-English couplet dataset |
| `prosody/` | Persian text normalization, metre patterns, scansion and rhythm scoring |
| `eval/` | baseline and fine-tuned translation evaluation |
| `training/` | fine-tuning script and notebook (full and LoRA) |
| `app/` | Gradio Space |
| `tests/` | unit tests |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Milestones

1. Dataset: verse-aligned Persian-English couplets with a held-out test split of at least 200 couplets
2. Baseline evaluation (BLEU, chrF) of NLLB-200-distilled-600M and mT5-base ParsiNLU
3. Fine-tuning (full and LoRA)
4. Gradio app on a Space
5. Recitation coach (word accuracy and metre feedback)

## Licensing notes

- Rumi's Persian text (13th century) is public domain. We take it from
  [Ganjoor](https://ganjoor.net) via [ganjoor/ganjoor-data](https://github.com/ganjoor/ganjoor-data)
  and credit Ganjoor for the digitization.
- English text comes only from public-domain translations (Whinfield 1898,
  Nicholson 1898 and 1926-1930, Redhouse 1881). See `data/sources.py` for the
  status of each edition. Modern translations (for example Coleman Barks or
  Arberry) are never used.
- `facebook/nllb-200-distilled-600M` is licensed CC BY-NC 4.0 (non-commercial),
  so a model fine-tuned from it inherits that restriction.
