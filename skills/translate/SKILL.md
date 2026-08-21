---
name: translate
description: Translate text between languages. Use for "translate", "translation", "how do you say ... in ...", "say this in English/Chinese/Japanese", "what does this mean in English".
---

## How to translate well

1. Detect the source language. If it's not obvious, state your guess and
   proceed ("Assuming this is Japanese…").
2. Translate for meaning, not word-for-word. Idioms, tone, and register should
   read naturally in the target language — a literal gloss that loses the tone
   is a failed translation.
3. Preserve formatting that matters: lists stay lists, code stays code, and
   numbers/dates/units stay as they are (convert units only if asked).
4. Keep names untranslated unless a well-known equivalent exists
   ("北京" stays "Beijing", but "中华人民共和国" → "People's Republic of China").
5. If a phrase is ambiguous or carries cultural weight (honorifics, puns),
   translate it and add a one-line note — don't silently flatten it.

## Edge cases

| Situation | Do |
|---|---|
| Mixed-language input | Translate the foreign parts, leave the already-target-language parts untouched, and say what you did |
| Technical or jargon text | Keep the jargon; gloss it in parentheses on first use |
| No target language given | Default to English; if the source is already English, default to Chinese and say so |
| A single word with many meanings | Give the most likely sense, then list 1-2 alternates with a one-line gloss |
