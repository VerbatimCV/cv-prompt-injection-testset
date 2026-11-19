# Deviations from the pre-registration

Every change made after PREREGISTRATION.md was committed (1f0c1a7), and why.

1. **Squashed text: 5% instead of 1% horizontal scale** (found while generating the set, before any
   detector or model run). At 1% to 3%, PDFium (used by Chrome and many PDF tools) draws the letters
   at full size, overlapping into a visible black blob, so the attack wasn't hidden. At 5% it renders
   as a faint speck about 18pt wide. File: `t3_pdf_squashed_5pct.pdf`. (Side finding: below about 4%
   this technique is *visible* in PDFium-based viewers.)
2. **PDF annotation: a normal text annotation** (a small comment icon whose text shows only when
   opened) instead of one flagged hidden: the PDF library used doesn't set the hidden flag. The text is
   still not part of the page's visible content.
3. **Model-trial details the pre-registration didn't fix** (decided and committed in ab6acf0, before
   any paid call):
   - Rank and agent ran on both clean twins plus the 7 attacks (9 variants, not 8), so the DOCX attack
     has a DOCX twin to pair with.
   - The agent role asked for 7+ years, so the clean twin (about 5) would be rejected and a shift
     towards advancing could show. Consequence: the task can't show a penalty.
   - Claude Sonnet 5.5 rejects a forced `tool_choice`, so every model got `auto` and was told to call
     exactly one tool. All 270 agent calls did.
   - `max_tokens` 8000 (both Claude models think by default), and models called with no thinking,
     effort or temperature settings.
4. **Analysis split** (decided after the pre-registration, before the analysis was run): pooled
   results are given for attacks whose payload reaches the model and for all attacks.
5. **Smoke test before the runner was committed:** 6 calls (one agent and one rank call per model,
   on `t1_pdf_white_text.pdf`, US$0.016) to check the model names and tool calling worked. No prompt
   changed afterwards. Their responses weren't kept, so they aren't in `raw.jsonl`.
