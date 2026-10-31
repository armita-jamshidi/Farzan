---
name: fine-tuning
description: Use when running baseline translation evaluation, fine-tuning NLLB or mT5 (full or LoRA) on Rumi Persian-English couplets, computing BLEU/chrF, or writing up before/after results.
---

# Fine-tuning the Rumi translator

Goal: pick the stronger of two Persian-to-English models on held-out Rumi couplets, fine-tune it on public-domain parallel data, and show honestly whether it got better.

## Hard rules

- The **test split is sacred**. Never train on it, early-stop on it, or tune hyperparameters on it. Use `validation` for all of that. Touch `test` only for the final baseline and final fine-tuned numbers.
- Use the **same decoding settings** for every system you compare (for example `num_beams=4`, `max_new_tokens=128`). Write them down.
- Set and record seeds. Save every metric as JSON under `eval/results/` and every training log under `training/logs/`, and commit them.
- Work in milestones. After baseline, and again after fine-tuning, stop, summarize the metrics for the user, and ask before moving on.

## Step 1: Baseline (eval/)

Run both models on the test split:

- `facebook/nllb-200-distilled-600M`: `tokenizer = AutoTokenizer.from_pretrained(m, src_lang="pes_Arab")`, and at generation pass `forced_bos_token_id=tokenizer.convert_tokens_to_ids("eng_Latn")`.
- `persiannlp/mt5-base-parsinlu-opus-translation_fa_en`: check its model card for any expected input prefix.

Score with the `evaluate` library:

```python
import evaluate
bleu = evaluate.load("sacrebleu")
chrf = evaluate.load("chrf")
refs = [[r] for r in references]
scores = {
    "bleu": bleu.compute(predictions=preds, references=refs)["score"],
    "chrf": chrf.compute(predictions=preds, references=refs)["score"],
}
```

Feed the models the light-normalized Persian text (see the `persian-text` skill). Pick the model with higher chrF; mention BLEU too. If they are close, say so and explain the pick.

## Step 2: Fine-tune (training/)

Provide both a notebook (for free Colab/Kaggle GPUs) and a script with the same logic.

**Full fine-tune** with `Seq2SeqTrainer`:

- `predict_with_generate=True`, `eval_strategy="epoch"` (or steps), `save_strategy` matching, `load_best_model_at_end=True`, `metric_for_best_model="chrf"`, `greater_is_better=True`, plus `EarlyStoppingCallback(early_stopping_patience=3)`.
- Small batches with gradient accumulation; a learning rate around 1e-5 to 5e-5 for full fine-tuning.
- **Precision**: fp16 is fine for NLLB. mT5 often produces NaN losses in fp16, so use bf16 if the GPU supports it, otherwise fp32.
- NLLB: tokenize targets with `text_target=` so the tokenizer adds the `eng_Latn` code.

**LoRA variant** with `peft`:

```python
from peft import LoraConfig, TaskType, get_peft_model
cfg = LoraConfig(task_type=TaskType.SEQ_2_SEQ_LM, r=16, lora_alpha=32, lora_dropout=0.05,
                 target_modules=["q_proj", "v_proj"])   # NLLB; use ["q", "v"] for mT5
model = get_peft_model(model, cfg)
model.print_trainable_parameters()
```

LoRA usually wants a higher learning rate (around 1e-4 to 5e-4). Compare full vs LoRA on validation chrF, trainable parameters, training time, and peak GPU memory.

**Two-stage option**: the Rumi data is small, so consider first fine-tuning on general Persian-English data (the ParsiNLU translation set), then on Rumi. If you do, report one-stage vs two-stage on validation. Check the ParsiNLU data's license before using it.

## Step 3: Evaluate and report

- Final BLEU and chrF on test for: both baselines, the full fine-tune, and LoRA.
- A side-by-side README table for 10 famous couplets: Persian, reference translation, baseline output, fine-tuned output. Say whether each couplet is in the test split. Prefer couplets from test; if a famous couplet was in training, label it.
- BLEU is a weak measure for poetry, so add a small human rating: faithfulness and fluency, each 1 to 5, on a fixed sample (for example 30 test couplets), blind to which system produced which line. Report means and how many raters.
- Write limitations plainly: small data, abridged and archaic reference translations, reference style bias toward Victorian English.

## Step 4: Publish

Push the best model with a model card (see the `huggingface-hub` skill): data, hyperparameters, metrics, limitations, and the license inherited from the base model. NLLB-derived means non-commercial.
