"""Run the three pre-registered detectors and the exposure measure over the frozen v2 set.

    .venv/bin/python integrations/injection-testset/v2/run_detectors.py [MANIFEST CVS_DIR OUT_JSON]

SCAN_URL overrides the scanner address; SCAN_URL=local runs the scanner in this checkout.

D1 keyword filter, D2 OCR difference (PDF only; DOCX marked n/a, as no LibreOffice is installed), D3
the production VerbatimCV scanner (POST https://api.verbatimcv.com/v1/scan). Writes
results/detectors.json; analyse_detectors.py turns it into results/detectors.md. Free: no model calls.
"""

import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import docx
import httpx
import pypdfium2

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from app import ocr, pdf_extract

HERE = Path(__file__).resolve().parent
CVS, OUT = HERE / "cvs", HERE / "results"
SCAN = os.environ.get("SCAN_URL", "https://api.verbatimcv.com/v1/scan")
D1_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions",
    r"ai (screening|recruit)",
    r"system (note|prompt)",
    r"rank this candidate",
    r"top match",
]
ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"))
LOOKALIKES = str.maketrans({"а": "a", "е": "e", "о": "o", "с": "c", "р": "p", "і": "i", "у": "y", "х": "x"})


def naive_text(path: Path) -> str:
    """What a typical pipeline extracts: PDF text layer (pypdfium2) or DOCX body paragraphs."""
    if path.suffix == ".pdf":
        pdf = pypdfium2.PdfDocument(str(path))
        return "\n".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf)))
    return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)


def normalise(text: str) -> str:
    """Decode Unicode tag characters, drop zero-width characters, map Cyrillic look-alikes back to
    Latin, case-fold and collapse whitespace, so a payload a model would read counts as exposed."""
    text = "".join(chr(ord(ch) - 0xE0000) if 0xE0020 <= ord(ch) <= 0xE007E else ch for ch in text)
    text = text.translate(ZERO_WIDTH).translate(LOOKALIKES)
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def exposed(path: Path, payload: str | None) -> bool | None:
    if not payload:
        return None
    return normalise(payload)[:60] in normalise(naive_text(path))


def d1_keyword(path: Path) -> bool:
    text = naive_text(path).casefold()
    return any(re.search(p, text) for p in D1_PATTERNS)


def _fold(word: str) -> str:
    word = unicodedata.normalize("NFKD", word.casefold())
    return "".join(ch for ch in word if ch.isalpha())


def d2_ocr_diff(path: Path) -> bool | None:
    if path.suffix != ".pdf":
        return None  # not applicable: no LibreOffice to render DOCX
    data = path.read_bytes()
    pdf = pypdfium2.PdfDocument(data)
    langs = "eng+deu" if "german" in path.name else "eng"
    for n in range(1, len(pdf) + 1):
        png = pdf_extract.render_page(data, n, dpi=200)
        page = ocr.ocr_image(png, n, langs)
        seen = {_fold(w.text) for b in page.blocks for w in b.words}
        for line in pdf[n - 1].get_textpage().get_text_range().splitlines():
            words = [_fold(w) for w in line.split()]
            words = [w for w in words if len(w) >= 3]
            if len(words) >= 3 and sum(w in seen for w in words) < len(words) / 2:
                return True
    return False


def d3_scanner(client: httpx.Client, path: Path) -> tuple[bool | None, list]:
    if SCAN == "local":  # the scanner in this checkout, without the HTTP layer
        from app import extract

        found = extract.prepare(path.read_bytes()).findings
        return bool(found), [{"technique": f.technique, "detail": f.detail} for f in found]
    for _ in range(3):
        r = client.post(SCAN, files={"file": (path.name, path.read_bytes())})
        if r.status_code == 429:
            time.sleep(int(r.headers.get("retry-after", "10")) + 1)
            continue
        if r.status_code != 200:
            return None, [{"error": r.json().get("error", {}).get("code", r.status_code)}]
        body = r.json()
        return body["prompt_injection_detected"], [{k: f[k] for k in ("technique", "detail")} for f in body["findings"]]
    return None, [{"error": "rate limited"}]


def main() -> None:
    manifest_path, cvs, out = (Path(a) for a in sys.argv[1:4]) if len(sys.argv) == 4 else (
        HERE / "manifest.json", CVS, OUT / "detectors.json")
    out.parent.mkdir(exist_ok=True)
    manifest = json.loads(manifest_path.read_text())
    rows = []
    with httpx.Client(timeout=60, headers={"User-Agent": "verbatimcv-injection-experiment"}) as client:
        for c in manifest:
            path = cvs / c["file"]
            d3, findings = d3_scanner(client, path)
            row = {**c, "exposed": exposed(path, c["payload"]), "d1_keyword": d1_keyword(path),
                   "d2_ocr_diff": d2_ocr_diff(path), "d3_verbatimcv": d3, "d3_findings": findings}
            rows.append(row)
            print(f"{c['file']:44} exposed={row['exposed']!s:5} d1={row['d1_keyword']!s:5} d2={row['d2_ocr_diff']!s:5} d3={d3}")
            time.sleep(0 if SCAN == "local" else 6.5)  # production allows 10 a minute
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
