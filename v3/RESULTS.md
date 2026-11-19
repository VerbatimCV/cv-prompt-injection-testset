# Scanner v3: before and after

Production `/v1/scan`, 2026-11-19. Scanner v2 = before (app code e470e3a); scanner v3 = after (f5c3a33).
Raw results in `results/`. The v2 results in `../v2/results/` are unchanged.

| Set | Scanner v2 | Scanner v3 |
|---|---|---|
| **Held-out set** (15 attacks, 6 controls; committed in 1dabe42 before any scanner change) | 6/15 caught, 1/6 false alarms | **14/15 caught, 0/6 false alarms** |
| v2 set (27 attacks, 8 controls; v3 was tuned on it) | 16/27 caught, 2/8 false alarms | 25/27 caught, 0/8 false alarms |
| v1 set (10 attacks, 4 controls) | 14/14 correct | 14/14 correct |
| Golden set (2 hidden-text CVs, 18 clean) | 2/2, 0/18 | 2/2, 0/18; model input byte-identical |

## Still missed

- **Polish instruction** (held-out h05). Polish patterns were left out on purpose to check how well
  the change generalises: languages without patterns are still missed.
- **Text painted inside an image** (v2). Only the text layer is read.
- **Unicode tag characters in a PDF** (v2). PDFium, which the parser uses, drops them, so they never
  reach the model through VerbatimCV. Other PDF libraries might keep them. Tag characters in Word
  files are now caught (held-out h14).

## Fixed after the first deploy (same day)

- **False alarms on ordinary CV lines.** A sweep of 63 normal recruiter, HR, AI and security lines
  flagged 17 with the first v3 patterns, including two that came from older patterns. In `/v1/parse`
  that would have removed real CV text for about 40 minutes. The patterns are now tighter, and 0 of
  the 63 are flagged; they're kept as regression tests.
- **Wrapped instructions.** Only the matching line used to be removed, so a continuation line such as
  "...and state 15 years of experience" still reached the model. The check now covers whole
  paragraphs. Detection numbers didn't change.

## Caveats

- We wrote the attacks, the held-out set and the scanner. The held-out set was frozen before the
  scanner change, but its languages (French, Italian, Portuguese), its look-alike alphabet (Greek) and
  its phrasing were known while the new patterns were written. That flatters the held-out result. A
  fair test needs attacks written by someone else.
- One file per technique, so every rate has a wide interval.
- Matching visible text is a trade-off: in `/v1/parse`, flagged text is removed before extraction.
  New patterns were checked against 18 clean golden CVs, 14 controls and unit-test sentences (brag
  lines, a recruiter's CV, security work, Greek and Cyrillic names), but real CVs will turn up false
  alarms we haven't seen.
