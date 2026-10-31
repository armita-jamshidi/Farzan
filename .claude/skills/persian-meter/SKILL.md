---
name: persian-meter
description: Use when encoding classical Persian meters ('aruz), scanning a Rumi couplet into long and short syllables, or scoring a user's recitation rhythm and pauses against the meter in the practice coach.
---

# Persian meter ('aruz) and rhythm scoring

The practice coach checks whether the user's long syllables are held longer than their short ones and whether they pause at the middle of the couplet. This lives in `prosody/`. Scansion is easy to get subtly wrong, so every pattern and rule must be spot-checked by a Persian speaker or a reliable reference (for example the meter Ganjoor lists for each poem, or Elwell-Sutton's *The Persian Metres*). Tell the user which verses were checked and by whom.

## Notation

Store a meter as a string of syllable weights for one hemistich (misra'):

- `-` long, `u` short, `x` anceps (either is allowed)
- `|` foot boundary, only for readability; strip it before matching

Keep a table of meters, in `prosody/meters.py`, with the Persian name, the transliterated name, the feet, and the pattern:

| Meter | Feet | Pattern (one hemistich) |
|---|---|---|
| ramal musaddas mahzuf (Masnavi) | fā'ilātun fā'ilātun fā'ilun | `x u - - \| - u - - \| - u -` |

The first `x` is there because in ramal the first syllable is often short (fa'ilātun for fā'ilātun). Every Masnavi couplet uses this meter. Divan ghazals use many meters, so take each ghazal's meter from its source (Ganjoor's meter label) and add it to the table only after checking its pattern.

## Scansion rules (from text to long/short)

Scan from the stored text with diacritics, before match-normalization.

1. Split each word into syllables. Persian syllables start with one consonant: CV, CVC, CVCC (V is a vowel).
2. Weights:
   - CV with a short vowel (a, e, o) is **short**.
   - CV with a long vowel (ā, ī, ū), and CVC with a short vowel, are **long**.
   - CV̄C (long vowel plus consonant) and CVCC are **overlong**, counted as long + short (`- u`).
3. The last syllable of a hemistich always counts as long, so an overlong syllable there is just long.
4. Common licenses to handle, and to flag for checking when used:
   - Ezafe (-e) and the conjunction "o" (و) can be short or long as the meter needs.
   - A vowel-initial word can join the previous consonant (the consonant moves forward), which can turn a long syllable into a short one.
   - `n` after a long vowel (ān, īn, ūn) often doesn't count, so the syllable is long rather than overlong.
   - Silent `h` at word end (as in خانه) is just the vowel e.
5. The script doesn't write short vowels, so an unvoweled word can be ambiguous. Resolve it by finding the reading that fits the known meter pattern, and record which words needed this.
6. Output per hemistich: a list of syllables with `(word_index, syllable_text, weight)`, plus whether it matched the meter. Store failures instead of forcing a match.

Write unit tests with a few hand-checked Masnavi couplets (for example the opening "بشنو این نی چون شکایت می‌کند") and their known patterns.

## Rhythm scoring from audio

1. Get word timestamps from Whisper (`return_timestamps="word"`). For syllable-level timing, use forced alignment (for example torchaudio's MMS forced aligner on a romanized form) and fall back to splitting each word's duration across its syllables by weight if alignment fails.
2. Map the user's words to the expected words using the `persian-text` alignment. Only score syllables in words the user said correctly.
3. Per syllable, compare duration to the user's own average syllable duration (to cancel out speaking speed).
   - A long syllable should be clearly longer than the neighbouring short ones (start with a ratio of about 1.3 and tune it on reference recordings).
   - Score = the share of long/short neighbour pairs in the right order, plus partial credit for overlong syllables. Skip `x` positions.
4. Hemistich pause: the gap between the last word of hemistich 1 and the first word of hemistich 2 should be clearly longer than the user's typical gap between words (start with 2x the median gap, or at least about 250 ms).
5. Compare overall tempo (syllables per second) and pause positions to the reference recitation from the TTS model.
6. Calibrate thresholds on a few recordings (TTS reference, and human readings if the user can provide them). Write the chosen thresholds and why in the code.

## Feedback

Turn scores into a few short, plain sentences, most important first, at most three:

- "Hold the second syllable of «شکایت» longer."
- "Pause at the middle of the couplet, after «کند»."
- "You read this a bit faster than the reference. Try slowing down."

Always show, near the feedback: this is an automated coach and can be wrong, especially with unusual pronunciations or regional accents. If timing data is unreliable (too many wrong words, alignment failed), say so instead of giving rhythm advice.

## Tests (required)

`pytest` tests for: syllable weight rules, the overlong-at-end rule, matching a scanned hemistich against a pattern with `x`, and the rhythm score on synthetic timings (perfect timing scores high, reversed long/short scores low, a missing hemistich pause is reported).
