---
name: persian-text
description: Use when cleaning, normalizing, tokenizing, or comparing Persian (Farsi) text, including dataset cleaning, model input prep, and word error rate between a Whisper transcript and the expected couplet.
---

# Persian text handling

Persian text from Ganjoor, model outputs, and Whisper transcripts uses inconsistent Unicode. The same word can look identical on screen but compare as different strings. All Persian text handling goes through the shared module `prosody/normalize.py` (entry points `normalize(text) -> str` and `tokenize(text) -> list[str]`), which has unit tests. Don't write ad hoc `str.replace` calls in other files.

## Two levels of normalization

The module needs two levels, and every caller must pick the right one (for example a `light` option on `normalize`, or two functions):

1. **`normalize_light(text)`**: for storing in the dataset, feeding translation models, and display. Keeps diacritics (harakat), because the meter scanner needs them.
2. **`normalize_for_match(text)`**: for comparing words (WER, alignment, highlighting). Applies `normalize_light` and then strips everything that does not change which word was said.

### normalize_light

- Unicode NFC first.
- Arabic yeh `ي` (U+064A) and alef maksura `ى` (U+0649) become Persian yeh `ی` (U+06CC).
- Arabic kaf `ك` (U+0643) becomes Persian keheh `ک` (U+06A9).
- Arabic-Indic digits `٠-٩` and Persian digits `۰-۹`: pick one form (ASCII for matching, Persian for display) and be consistent.
- Remove tatweel `ـ` (U+0640).
- Turn any run of whitespace into a single space, and trim.
- Keep the zero-width non-joiner (ZWNJ, U+200C), but collapse repeats and remove ZWNJ next to a space or at the start/end of a word.

### normalize_for_match (on top of light)

- Remove diacritics: U+064B to U+0652 (tanwin, fatha, damma, kasra, shadda, sukun), U+0670 (superscript alef), U+0654 and U+0655 (hamza above/below).
- Map `ۀ` (U+06C0) and `ة` (U+0629) to `ه`. Map `أ` `إ` `ٱ` to `ا`, and `ؤ` to `و`. Leave `آ` alone, since it is a different letter in Persian.
- ZWNJ: replace it with nothing, so `می‌روم`, `می روم`, and `میروم` all match. Whisper is inconsistent here, so do the same to both sides.
- Remove punctuation: `، ؛ ؟ « » . , ! : ( ) -` and the Ganjoor hemistich separators.
- Then split on whitespace to get words.

Always apply exactly the same function to the reference and the hypothesis. Most WER bugs come from normalizing only one side.

## Word error rate and highlighting

- Use `jiwer` (or `evaluate.load("wer")`) on the match-normalized strings.
- For highlighting, align reference and hypothesis words (jiwer's alignment output, or a Levenshtein alignment) and tag each reference word as correct, substituted, or deleted, and list inserted words. Show the user the **original** words (from `normalize_light`), not the stripped forms.
- A couplet is two hemistichs (misra'). Keep track of which hemistich each word belongs to so feedback can say "in the second half".

## Things to watch

- Don't drop ezafe or short vowels from the stored dataset text. The meter skill needs them.
- Ganjoor sometimes marks hemistich boundaries with special characters or separate fields. Preserve the boundary as data (two fields, or a fixed separator) before normalizing.
- Persian is right-to-left. In Gradio, wrap Persian output with `dir="rtl"` so punctuation and mixed text display correctly.
- `hazm` and `parsivar` have normalizers you can compare against, but keep our own rules explicit and tested so behaviour doesn't change when a library updates.

## Tests (required)

Add small `pytest` tests in `tests/` covering: Arabic vs Persian yeh and kaf, diacritics removed only in match mode, ZWNJ variants matching, tatweel, digits, punctuation, and a full WER example where Arabic-form input against Persian-form reference gives WER 0.
