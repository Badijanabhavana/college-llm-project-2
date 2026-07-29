# -*- coding: utf-8 -*-
"""
fetch_and_index.py
──────────────────
Step 1 — Fetches every official JNTU-GV URL found in the project.
Step 2 — Extracts clean text from each page (HTML + PDF).
Step 3 — Saves everything to scraped_data.json.
Step 4 — Loads all entries into the RAG vector index used by the chatbot.

Run once (or whenever you want to refresh the knowledge base):
    python fetch_and_index.py

Options:
    python fetch_and_index.py --json-only   # save JSON, skip RAG loading
    python fetch_and_index.py --rag-only    # skip fetching, reload JSON into RAG
"""

import os, re, sys, json, time, argparse, io
from urllib.parse import urljoin
from datetime import datetime

import requests
from bs4 import BeautifulSoup, Comment

# ─────────────────────────────────────────────────────────────────────────────
# ALL URLS discovered from the project (rag.py, scrape_college.py, app.py,
# link_resolver.py, fetch_*.py).  Deduplicated and categorised.
# ─────────────────────────────────────────────────────────────────────────────
SOURCES = [
    # ── Core pages ───────────────────────────────────────────────────────────
    {"url": "https://jntugvcev.edu.in/",
     "label": "JNTU-GV College of Engineering Vizianagaram — Home", "category": "General"},

    {"url": "https://jntugv.edu.in/",
     "label": "JNTU-GV University — Official Portal", "category": "General"},

    {"url": "https://www.jntugv.edu.in/",
     "label": "JNTU-GV University Website (www)", "category": "General"},

    # ── University-level pages (jntugv.edu.in) ────────────────────────────
    {"url": "https://jntugv.edu.in/results",
     "label": "JNTU-GV Examination Results Portal", "category": "Examinations"},

    {"url": "https://jntugv.edu.in/notifications",
     "label": "JNTU-GV University Notifications", "category": "Notifications"},

    {"url": "https://jntugv.edu.in/academics",
     "label": "JNTU-GV University Academics", "category": "Programs"},

    {"url": "https://jntugv.edu.in/admissions",
     "label": "JNTU-GV University Admissions", "category": "Admissions"},

    {"url": "https://jntugv.edu.in/departments",
     "label": "JNTU-GV University Departments", "category": "Departments"},

    {"url": "https://jntugv.edu.in/examination",
     "label": "JNTU-GV University Examination Branch", "category": "Examinations"},

    {"url": "https://jntugv.edu.in/regulations",
     "label": "JNTU-GV University Academic Regulations", "category": "Regulations"},

    # ── College-level pages (jntugvcev.edu.in) ────────────────────────────
    {"url": "https://jntugvcev.edu.in/admistration/",
     "label": "Administration and Leadership", "category": "Administration"},

    {"url": "https://jntugvcev.edu.in/contact-us/telephone-directory/",
     "label": "Contact and Telephone Directory", "category": "Contact"},

    # ── Academics ────────────────────────────────────────────────────────────
    {"url": "https://jntugvcev.edu.in/academics/courses-offered/",
     "label": "Courses Offered", "category": "Programs"},

    {"url": "https://jntugvcev.edu.in/academics/admissions/admission-procedure/",
     "label": "Admission Procedure", "category": "Admissions"},

    {"url": "https://jntugvcev.edu.in/academics/admissions/fee-structure/",
     "label": "Fee Structure", "category": "Fees"},

    # ── Examinations ─────────────────────────────────────────────────────────
    {"url": "https://jntugvcev.edu.in/academics/examinations/results/",
     "label": "Examination Results", "category": "Examinations"},

    {"url": "https://jntugvcev.edu.in/academics/examinations/examination-time-tables/",
     "label": "Examination Timetables and Notifications", "category": "Timetables"},

    {"url": "https://jntugvcev.edu.in/notifications/",
     "label": "Latest Notifications", "category": "Notifications"},

    # ── Departments ──────────────────────────────────────────────────────────
    {"url": "https://jntugvcev.edu.in/departments/cse/",
     "label": "CSE Department", "category": "Departments"},

    {"url": "https://jntugvcev.edu.in/departments/ece/",
     "label": "ECE Department", "category": "Departments"},

    {"url": "https://jntugvcev.edu.in/departments/eee/",
     "label": "EEE Department", "category": "Departments"},

    {"url": "https://jntugvcev.edu.in/departments/mechanical/",
     "label": "Mechanical Engineering Department", "category": "Departments"},

    {"url": "https://jntugvcev.edu.in/departments/civil/",
     "label": "Civil Engineering Department", "category": "Departments"},

    {"url": "https://jntugvcev.edu.in/departments/it/",
     "label": "IT Department — Information Technology", "category": "Departments"},

    {"url": "https://jntugvcev.edu.in/departments/pharmacy/",
     "label": "Pharmacy Department", "category": "Departments"},

    # ── Placements / Facilities / Student life ────────────────────────────────
    {"url": "https://jntugvcev.edu.in/beta/placements/training-placements-cell/",
     "label": "Training and Placements Cell", "category": "Placements"},

    {"url": "https://jntugvcev.edu.in/facilities/library/",
     "label": "Central Library", "category": "Facilities"},

    {"url": "https://jntugvcev.edu.in/facilities/hostels/",
     "label": "Hostels", "category": "Facilities"},

    {"url": "https://jntugvcev.edu.in/rd-cell/about-research/",
     "label": "R&D Cell – Research", "category": "Research"},

    {"url": "https://jntugvcev.edu.in/student-corner/nss/",
     "label": "NSS and Student Corner", "category": "Student Activities"},

    {"url": "https://jntugvcev.edu.in/gallery/",
     "label": "Events and Gallery", "category": "Events"},
]

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
OUTPUT_JSON    = "scraped_data.json"
HEADERS        = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT        = 15
DELAY          = 1.0          # polite pause between requests
MAX_TEXT_CHARS = 6000         # per page after cleaning

# Tags whose entire content we delete
DROP_TAGS = {"script", "style", "noscript", "nav", "header", "footer",
             "aside", "form", "iframe", "svg", "button", "head"}

# Regex to detect noisy class/id names
NOISE_RE = re.compile(
    r"nav|menu|footer|header|sidebar|breadcrumb|cookie|banner|"
    r"social|share|advert|widget|popup|modal|pagination|topbar|navbar",
    re.I,
)


# ─────────────────────────────────────────────────────────────────────────────
# Extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def _noisy(tag) -> bool:
    for attr in ("class", "id"):
        v = tag.get(attr, "")
        if isinstance(v, list):
            v = " ".join(v)
        if NOISE_RE.search(v):
            return True
    return False


def _pdf_links(soup: BeautifulSoup, base: str) -> list[str]:
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().endswith(".pdf"):
            links.append(urljoin(base, href))
    return links


def extract_html(html: str, base_url: str) -> tuple[str, list[str]]:
    """Return (clean_text, pdf_link_list)."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove comments
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()

    # Drop noisy structural tags
    for tag in soup.find_all(DROP_TAGS):
        tag.decompose()

    # Drop noisy divs/sections
    for tag in soup.find_all(True):
        if _noisy(tag):
            tag.decompose()

    pdfs = _pdf_links(soup, base_url)

    raw = soup.get_text(separator="\n")

    # Deduplicate and clean lines
    seen, lines = set(), []
    for line in raw.splitlines():
        line = line.strip()
        if not line or len(line) < 4:
            continue
        key = re.sub(r"\s+", " ", line.lower())
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)

    text = "\n".join(lines)
    return text[:MAX_TEXT_CHARS], pdfs


def extract_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber → PyPDF2 fallback."""
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                t = page.extract_text()
                if t:
                    pages.append(f"[Page {i}]\n{t.strip()}")
        return "\n\n".join(pages)[:MAX_TEXT_CHARS]
    except ImportError:
        pass
    except Exception as e:
        print(f"  pdfplumber error: {e}")

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for i, page in enumerate(reader.pages, 1):
            t = page.extract_text()
            if t:
                pages.append(f"[Page {i}]\n{t.strip()}")
        return "\n\n".join(pages)[:MAX_TEXT_CHARS]
    except ImportError:
        print("  WARNING: Install pdfplumber → pip install pdfplumber")
        return ""
    except Exception as e:
        print(f"  PyPDF2 error: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Fetch one source
# ─────────────────────────────────────────────────────────────────────────────

def fetch_source(src: dict) -> dict | None:
    url      = src["url"]
    label    = src["label"]
    category = src["category"]
    print(f"  → {label}")
    print(f"    {url}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"    ✗ FAILED: {e}")
        return None

    ct = r.headers.get("Content-Type", "").lower()

    if "pdf" in ct or url.lower().endswith(".pdf"):
        text = extract_pdf(r.content)
        pdfs = [url]
    elif "html" in ct or "text" in ct:
        enc = r.encoding or "utf-8"
        html = r.content.decode(enc, errors="replace")
        text, pdfs = extract_html(html, url)
    else:
        print(f"    ✗ Unsupported content-type: {ct}")
        return None

    if not text.strip():
        print(f"    ✗ No text extracted")
        return None

    print(f"    ✓ {len(text)} chars, {len(pdfs)} PDF links")

    return {
        "title":     f"{category} — {label}",
        "label":     label,
        "category":  category,
        "url":       url,
        "text":      text,
        "pdf_links": pdfs,
        "scraped_at": datetime.utcnow().isoformat() + "Z",
    }


# ─────────────────────────────────────────────────────────────────────────────
# JSON persistence
# ─────────────────────────────────────────────────────────────────────────────

def save_json(entries: list[dict]) -> None:
    payload = {
        "meta": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_entries": len(entries),
            "source": "fetch_and_index.py",
        },
        "entries": entries,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    size = os.path.getsize(OUTPUT_JSON)
    print(f"\n✓ Saved {OUTPUT_JSON}  ({size:,} bytes, {len(entries)} entries)")


def load_json() -> list[dict]:
    if not os.path.exists(OUTPUT_JSON):
        return []
    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("entries", data) if isinstance(data, dict) else data


# ─────────────────────────────────────────────────────────────────────────────
# RAG integration
# ─────────────────────────────────────────────────────────────────────────────

def _chunk(text: str, size: int = 900, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks on line boundaries."""
    lines   = text.splitlines()
    chunks, cur, cur_len = [], [], 0
    for line in lines:
        ll = len(line) + 1
        if cur_len + ll > size and cur:
            chunks.append("\n".join(cur))
            # overlap: keep last ~overlap chars worth of lines
            tail, tl = [], 0
            for l in reversed(cur):
                tl += len(l) + 1
                tail.insert(0, l)
                if tl >= overlap:
                    break
            cur, cur_len = tail, tl
        cur.append(line)
        cur_len += ll
    if cur:
        chunks.append("\n".join(cur))
    return [c.strip() for c in chunks if c.strip()]


def load_into_rag(entries: list[dict]) -> None:
    print("\n── Loading into RAG vector index ──")
    try:
        from rag import rag_engine
    except ImportError:
        print("  ERROR: Cannot import rag.py — run from the project folder.")
        return

    loaded = skipped = 0
    for entry in entries:
        text = entry.get("text", "").strip()
        if not text:
            skipped += 1
            continue

        base_title = entry["title"]
        url        = entry["url"]
        chunks     = _chunk(text)

        for i, chunk in enumerate(chunks, 1):
            t = base_title if len(chunks) == 1 else f"{base_title} [part {i}/{len(chunks)}]"
            # Append the source URL to every chunk so the LLM can cite it
            content_with_url = f"{chunk}\n\nSource URL: {url}"

            # Also embed PDF links found on this page
            if i == 1 and entry.get("pdf_links"):
                pdf_section = "\nDirect PDF links from this page:\n" + "\n".join(
                    f"  - {lnk}" for lnk in entry["pdf_links"][:10]
                )
                content_with_url += pdf_section

            try:
                rag_engine.add_document(
                    title    = t,
                    content  = content_with_url,
                    source   = "fetch_and_index",
                    added_by = "auto_scraper",
                )
                loaded += 1
            except Exception as e:
                print(f"  RAG error on '{t}': {e}")
                skipped += 1

    print(f"  ✓ Loaded   : {loaded} chunks")
    print(f"  ✗ Skipped  : {skipped}")
    print(f"  Total docs : {rag_engine.doc_count}")


# ─────────────────────────────────────────────────────────────────────────────
# Keyword search over scraped_data.json (used by chatbot as fast fallback)
# ─────────────────────────────────────────────────────────────────────────────

def search_scraped(query: str, top_k: int = 4) -> list[dict]:
    """
    Search scraped_data.json by keyword overlap.
    Returns list of {"title", "url", "snippet", "score"}.
    Called by app.py when RAG returns no confident results.
    Always returns a list — never raises, never returns None.
    """
    try:
        entries = load_json()
    except Exception:
        return []

    if not entries:
        return []

    stop = {"the", "a", "an", "of", "in", "for", "and", "to", "is", "are",
            "what", "how", "when", "where", "which", "tell", "me", "about",
            "i", "my", "can", "do", "does", "please"}

    q_words = set(re.sub(r"[^\w\s]", "", query.lower()).split()) - stop
    if not q_words:
        return []

    scored = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        # Support both "title" (new format) and "label" (old format)
        title   = entry.get("title") or entry.get("label") or ""
        url     = entry.get("url") or ""
        text    = entry.get("text") or entry.get("content") or ""

        if not title or not url:
            continue

        body    = (text + " " + title).lower()
        e_words = set(re.sub(r"[^\w\s]", "", body).split())
        hits    = q_words & e_words
        if not hits:
            continue

        score = len(hits) / len(q_words)

        # Snippet: first line containing a hit word
        snippet = ""
        for line in text.splitlines():
            if any(w in line.lower() for w in hits):
                snippet = line.strip()[:400]
                break
        if not snippet:
            snippet = text[:400]

        scored.append({
            "title":   title,
            "url":     url,
            "snippet": snippet,
            "score":   round(score, 3),
        })
        

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch JNTU-GV pages → scraped_data.json → RAG")
    parser.add_argument("--json-only", action="store_true",
                        help="Save JSON only, skip RAG loading")
    parser.add_argument("--rag-only",  action="store_true",
                        help="Skip fetching, reload existing JSON into RAG")
    args = parser.parse_args()

    # ── Re-index existing JSON without re-fetching ────────────────────────
    if args.rag_only:
        entries = load_json()
        if not entries:
            print(f"ERROR: {OUTPUT_JSON} not found or empty. Run without --rag-only first.")
            sys.exit(1)
        print(f"Re-loading {len(entries)} entries from {OUTPUT_JSON} into RAG …")
        load_into_rag(entries)
        return

    # ── Fetch all sources ─────────────────────────────────────────────────
    print("=" * 60)
    print("JNTU-GV Knowledge Fetcher")
    print(f"Fetching {len(SOURCES)} sources …")
    print("=" * 60)

    entries: list[dict] = []
    failed:  list[str]  = []

    for i, src in enumerate(SOURCES, 1):
        print(f"\n[{i}/{len(SOURCES)}] {src['category']}")
        try:
            result = fetch_source(src)
            if result:
                entries.append(result)
            else:
                failed.append(src["url"])
        except Exception as e:
            print(f"  UNEXPECTED ERROR: {e}")
            failed.append(src["url"])

        if i < len(SOURCES):
            time.sleep(DELAY)

    # ── Save JSON ─────────────────────────────────────────────────────────
    if not entries:
        print("\nNo entries fetched. scraped_data.json not written.")
        sys.exit(1)

    save_json(entries)

    # ── Load into RAG ─────────────────────────────────────────────────────
    if not args.json_only:
        load_into_rag(entries)

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DONE")
    print(f"  Attempted : {len(SOURCES)}")
    print(f"  Succeeded : {len(entries)}")
    print(f"  Failed    : {len(failed)}")
    if failed:
        for u in failed:
            print(f"    ✗ {u}")
    print(f"  Output    : {OUTPUT_JSON}")
    print("=" * 60)


if __name__ == "__main__":
    main()
