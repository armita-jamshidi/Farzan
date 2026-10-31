---
name: huggingface-hub
description: Use when finding, downloading, or checking models and datasets on the Hugging Face Hub, pushing the Rumi dataset or fine-tuned model, writing dataset/model cards, or deploying the Farzan Gradio Space.
---

# Hugging Face Hub for Farzan

Farzan uses the Hub for three things: the verse-aligned Rumi dataset, the fine-tuned Persian-to-English model, and the live Gradio Space. Everything published must be honest about sources, licenses, and limitations.

## Ground rules

- Authenticate with the `HF_TOKEN` environment variable (or `huggingface-cli login`). Never write a token into code, notebooks, logs, or commits.
- Use `huggingface_hub.HfApi` for Hub operations (`model_info`, `dataset_info`, `list_datasets`, `create_repo`, `upload_folder`). Use `datasets.Dataset.push_to_hub` for the dataset.
- Push to the user's own account. Ask for the exact repo names before the first push; until then use placeholders like `<hf-user>/rumi-fa-en`.
- Publishing is outward-facing. Do a dry run (print the card and the split sizes) and confirm with the user before the first push of any repo.

## Before using any model

For every model the project touches, read the model card and record in the README's model table: license, whether it is gated, reported metrics, and anything the card says about Persian.

```python
from huggingface_hub import HfApi
info = HfApi().model_info("facebook/nllb-200-distilled-600M")
print(info.card_data.get("license"), info.gated, info.pipeline_tag)
```

Models named in the brief:

| Role | Model | Notes to verify |
|---|---|---|
| Translation | `facebook/nllb-200-distilled-600M` | CC-BY-NC-4.0, non-commercial. Say so in the README and in the fine-tuned model card. Languages `pes_Arab` to `eng_Latn`. |
| Translation | `persiannlp/mt5-base-parsinlu-opus-translation_fa_en` | Check license and the input format the card expects. |
| Explanation (optional) | `universitytehran/PersianMind-v1.0` or another small instruct model | Check license and gating. |
| TTS | `Thomcles/Chatterbox-TTS-Persian-Farsi` | Listen to real outputs before relying on it. |
| ASR | `givia/whisper-large-v3-turbo-persian` vs `openai/whisper-large-v3-turbo` | Compare WER on our couplets, use word timestamps. |

If a card is missing a license or is ambiguous, stop and ask the user. Do not guess.

## Dataset

1. **Search first.** Before scraping Ganjoor, search the Hub for existing Ganjoor-derived or Rumi datasets (`HfApi().list_datasets(search="ganjoor")`, also try "rumi", "masnavi", "persian poetry"). Report what exists, its license, and whether it has meter info. Reuse when the license allows.
2. **If scraping**, read ganjoor.net's terms and robots.txt first, rate-limit requests, cache raw pages locally, and record the scrape date.
3. **Schema**, one row per bayt (couplet):
   `source` (Masnavi | Divan), `book` or `poem` number, `verse` number, `persian_text`, `english_text`, `meter_name`, `translator`, `license_note`.
4. **English text** comes only from public-domain translations, such as E. H. Whinfield's abridged Masnavi (1887/1898) and older R. A. Nicholson translations. Check the public-domain status of each specific edition and write the reasoning in `license_note`. Copyright differs by country and publication date. If any edition is unclear, ask the user. Never use modern copyrighted translations (for example Coleman Barks), not even for evaluation.
5. **Splits**: `train`, `validation`, `test`. The test split has at least 200 couplets and is never used for training, tuning, or picking checkpoints. Split by poem or story section, not by random couplet, so neighbouring verses don't leak across splits. Fix the seed and save the split's IDs in the repo.
6. **Dataset card** (`README.md` in the dataset repo) must include YAML metadata (`language: [fa, en]`, `task_categories: [translation]`, `license`, `pretty_name`), then sections for sources with editions and URLs, licensing per translator, how alignment was done, split sizes, known alignment errors, and limitations (Whinfield is abridged, so many couplets have no English).

## Fine-tuned model

The model card must list: base model, training data (link the dataset), two-stage recipe if used, hyperparameters, BLEU and chrF before and after on the test split, the human rating results, limitations, and the license inherited from the base model (NLLB-based means non-commercial). Push with `trainer.push_to_hub()` or `upload_folder`, and include the eval JSON.

## Space (Gradio app)

- Space README YAML: `sdk: gradio`, `sdk_version`, `app_file: app.py`, `license`, and `models:` / `datasets:` links so the Hub shows the connections.
- Three tabs: Listen, Translate, Practice.
- Load every model once at module import, not per request. Use ZeroGPU (`import spaces`, decorate GPU functions with `@spaces.GPU`) or a small GPU if CPU is too slow.
- Pin versions in `requirements.txt`.
- Never store user recordings beyond the session unless the user opts in. Keep practice history in `gr.State`.
- Show a visible note that the practice coach is automated and can be wrong.
- After deploying, open the Space, run each tab once, and report what worked.
