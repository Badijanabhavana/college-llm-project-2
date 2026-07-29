# -*- coding: utf-8 -*-
"""
scrape_college.py
─────────────────
Automatically builds the JNTU-GV chatbot knowledge base from official sources.

What it does:
  1. Fetches every URL in SOURCES (HTML pages + PDF files).
  2. Extracts clean, readable text — strips navigation, footers, scripts, ads.
  3. Preserves: course names, fees, exam dates, timetables, faculty, PDF links.
  4. Deduplicates lines so repeated nav/footer text does not bloat the file.
  5. Saves everything to college_knowledge.txt.
  6. Loads each entry into the RAG vector index so the chatbot can search it
     semantically using sentence-transformers + FAISS.

Usage:
  python scrape_college.py            # scrape + save + load into RAG
  python scrape_college.py --txt-only # scrape + save only (skip RAG loading)

Dependencies (install once):
  pip install requests beautifulsoup4 pdfplumber
  (sentence-transformers and faiss-cpu are already in requirements.txt)
"""

import os
import re
import sys
import time
import argparse
import traceback
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Comment

# ──────────────────────────────────────────────────────────────────────────────
# SOURCES
# Every official JNTU-GV URL you want scraped.
# Add or remove URLs freely — the script handles both HTML and PDF automatically.
# ──────────────────────────────────────────────────────────────────────────────
SOURCES = [
    # ── Main college pages ──────────────────────────────────────────────────
    {
        "url":      "https://jntugvcev.edu.in/",
        "category": "Home",
        "label":    "JNTU-GV CEV Home Page",
    },
    {
        "url":      "https://jntugvcev.edu.in/academics/courses-offered/",
        "category": "Programs",
        "label":    "Courses Offered",
    },
    {
        "url":      "https://jntugvcev.edu.in/academics/admissions/admission-procedure/",
        "category": "Admissions",
        "label":    "Admission Procedure",
    },
    {
        "url":      "https://jntugvcev.edu.in/academics/admissions/fee-structure/",
        "category": "Fees",
        "label":    "Fee Structure",
    },
    {
        "url":      "https://jntugvcev.edu.in/academics/examinations/results/",
        "category": "Examinations",
        "label":    "Examination Results",
    },
    {
        "url":      "https://jntugvcev.edu.in/academics/examinations/examination-time-tables/",
        "category": "Timetables",
        "label":    "Examination Timetables",
    },
    {
        "url":      "https://jntugvcev.edu.in/notifications/",
        "category": "Notifications",
        "label":    "Latest Notifications",
    },
    {
        "url":      "https://jntugvcev.edu.in/admistration/",
        "category": "Administration",
        "label":    "Administration and Leadership",
    },
    {
        "url":      "https://jntugvcev.edu.in/beta/placements/training-placements-cell/",
        "category": "Placements",
        "label":    "Training and Placements Cell",
    },
    {
        "url":      "https://jntugvcev.edu.in/facilities/library/",
        "category": "Facilities",
        "label":    "Central Library",
    },
    {
        "url":      "https://jntugvcev.edu.in/facilities/hostels/",
        "category": "Facilities",
        "label":    "Hostels",
    },
    {
        "url":      "https://jntugvcev.edu.in/rd-cell/about-research/",
        "category": "Research",
        "label":    "R&D Cell / Research",
    },
    {
        "url":      "https://jntugvcev.edu.in/student-corner/nss/",
        "category": "Student Activities",
        "label":    "NSS and Student Corner",
    },
    {
        "url":      "https://jntugvcev.edu.in/contact-us/telephone-directory/",
        "category": "Contact",
        "label":    "Contact and Telephone Directory",
    },
    # ── Department pages ────────────────────────────────────────────────────
    {
        "url":      "https://jntugvcev.edu.in/departments/cse/",
        "category": "Departments",
        "label":    "CSE Department",
    },
    {
        "url":      "https://jntugvcev.edu.in/departments/ece/",
        "category": "Departments",
        "label":    "ECE Department",
    },
    {
        "url":      "https://jntugvcev.edu.in/departments/eee/",
        "category": "Departments",
        "label":    "EEE Department",
    },
    {
        "url":      "https://jntugvcev.edu.in/departments/mechanical/",
        "category": "Departments",
        "label":    "Mechanical Engineering Department",
    },
    {
        "url":      "https://jntugvcev.edu.in/departments/civil/",
        "category": "Departments",
        "label":    "Civil Engineering Department",
    },
    # ── PDF documents ───────────────────────────────────────────────────────
    # Add direct PDF URLs here as you find them.
    # Examples (replace with real URLs from the website):
    # {
    #     "url":      "https://jntugvcev.edu.in/wp-content/uploads/2025/01/fee-structure-2025.pdf",
    #     "category": "Fees",
    #     "label":    "Fee Structure 2025 PDF",
    # },
    # {
    #     "url":      "https://jntugvcev.edu.in/wp-content/uploads/2025/11/btech-ii-i-timetable.pdf",
    #     "category": "Timetables",
    #     "label":    "B.Tech II Year I-Semester Timetable Nov 2025",
    # },
]

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
OUTPUT_FILE   = "college_knowledge.txt"
REQUEST_DELAY = 1.2   # polite delay between requests (seconds)
REQUEST_TIMEOUT = 15
MAX_CONTENT_CHARS = 8000  # per page; keeps individual chunks manageable

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# HTML tags whose entire subtree we strip (not just the tag)
STRIP_TAGS = {
    "script", "style", "noscript", "header", "footer",
    "nav", "aside", "form", "iframe", "svg", "button",
    "meta", "link", "head",
}

# CSS class / id fragments that usually indicate navigation/footer noise
NOISE_PATTERNS = re.compile(
    r"nav|menu|footer|header|sidebar|breadcrumb|cookie|banner|"
    r"social|share|advertisement|ad-|widget|popup|modal|overlay|"
    r"topbar|navbar|pagination",
    re.IGNORECASE,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_noisy_tag(tag) -> bool:
    """Return True if this BeautifulSoup tag looks like nav/footer noise."""
    for attr in ("class", "id"):
        val = tag.get(attr, "")
        if isinstance(val, list):
            val = " ".join(val)
        if NOISE_PATTERNS.search(val):
            return True
    return False


def _extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Return all PDF/document href values found on the page."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        full = urljoin(base_url, href)
        # Keep only same-domain or PDF links
        parsed = urlparse(full)
        if "jntugvcev.edu.in" in parsed.netloc or "jntugv.edu.in" in parsed.netloc:
            links.append(full)
        elif full.lower().endswith(".pdf"):
            links.append(full)
    return links


def _clean_html(html: str, base_url: str) -> tuple[str, list[str]]:
    """
    Parse HTML, remove noise, extract clean text and document links.
    Returns (clean_text, list_of_pdf_links).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Remove script/style/nav/footer subtrees
    for tag in soup.find_all(STRIP_TAGS):
        tag.decompose()

    # Remove noisy divs/sections by class/id
    for tag in soup.find_all(True):
        if _is_noisy_tag(tag):
            tag.decompose()

    # Collect PDF/document download links BEFORE stripping <a> tags
    pdf_links = [
        urljoin(base_url, a["href"])
        for a in soup.find_all("a", href=True)
        if a["href"].lower().endswith((".pdf", ".doc", ".docx"))
    ]

    # Collect all other useful links (notifications, timetables)
    all_links = _extract_links(soup, base_url)

    # Get text
    text = soup.get_text(separator="\n")

    # Normalise whitespace
    lines = []
    seen  = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        # Skip blank, very short, or duplicate lines
        if not line or len(line) < 4:
            continue
        norm = re.sub(r"\s+", " ", line.lower())
        if norm in seen:
            continue
        seen.add(norm)
        lines.append(line)

    clean = "\n".join(lines)
    return clean[:MAX_CONTENT_CHARS], pdf_links + all_links


def _extract_pdf(pdf_bytes: bytes, source_url: str) -> str:
    """
    Extract text from a PDF byte string using pdfplumber (preferred)
    or PyPDF2 as fallback.
    """
    # ── Try pdfplumber first ──────────────────────────────────────────────
    try:
        import pdfplumber
        import io
        pages_text = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                t = page.extract_text()
                if t:
                    pages_text.append(f"[Page {i + 1}]\n{t.strip()}")
        if pages_text:
            combined = "\n\n".join(pages_text)
            return combined[:MAX_CONTENT_CHARS]
    except ImportError:
        pass
    except Exception as e:
        print(f"  [pdfplumber error] {e}")

    # ── Fallback: PyPDF2 ─────────────────────────────────────────────────
    try:
        import PyPDF2
        import io
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages):
            t = page.extract_text()
            if t:
                pages_text.append(f"[Page {i + 1}]\n{t.strip()}")
        combined = "\n\n".join(pages_text)
        return combined[:MAX_CONTENT_CHARS]
    except ImportError:
        print("  [WARNING] Neither pdfplumber nor PyPDF2 is installed.")
        print("  Run: pip install pdfplumber")
        return ""
    except Exception as e:
        print(f"  [PyPDF2 error] {e}")
        return ""


def _fetch_url(url: str) -> tuple[bytes | None, str]:
    """
    Fetch a URL.
    Returns (raw_bytes, content_type_string).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").lower()
        return resp.content, content_type
    except requests.exceptions.HTTPError as e:
        print(f"  [HTTP {e.response.status_code}] {url}")
    except requests.exceptions.ConnectionError:
        print(f"  [CONNECTION ERROR] Cannot reach {url}")
    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {url}")
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
    return None, ""


# ──────────────────────────────────────────────────────────────────────────────
# Core scraper
# ──────────────────────────────────────────────────────────────────────────────

def scrape_source(source: dict) -> dict | None:
    """
    Scrape one source entry.
    Returns a dict ready for writing to the knowledge file and loading into RAG.
    """
    url      = source["url"]
    category = source.get("category", "General")
    label    = source.get("label", url)

    print(f"\n[{category}] {label}")
    print(f"  → {url}")

    raw_bytes, content_type = _fetch_url(url)
    if raw_bytes is None:
        print("  ✗ Skipped (fetch failed)")
        return None

    extracted_text = ""
    doc_links      = []

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        # ── PDF ──────────────────────────────────────────────────────────
        print("  → Detected as PDF — extracting text …")
        extracted_text = _extract_pdf(raw_bytes, url)
        if extracted_text:
            print(f"  ✓ Extracted {len(extracted_text)} chars from PDF")
        else:
            print("  ✗ PDF extraction returned empty text")
            return None

    elif "html" in content_type or "text" in content_type:
        # ── HTML page ────────────────────────────────────────────────────
        try:
            html = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            html = raw_bytes.decode("latin-1", errors="replace")

        extracted_text, doc_links = _clean_html(html, url)

        if not extracted_text.strip():
            print("  ✗ No usable text extracted from page")
            return None

        print(f"  ✓ Extracted {len(extracted_text)} chars, {len(doc_links)} links")

    else:
        print(f"  ✗ Unsupported content type: {content_type}")
        return None

    return {
        "title":    f"{category} — {label}",
        "url":      url,
        "category": category,
        "label":    label,
        "content":  extracted_text,
        "links":    doc_links,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Knowledge file writer
# ──────────────────────────────────────────────────────────────────────────────

def write_knowledge_file(entries: list[dict], output_path: str) -> None:
    """Write all scraped entries to college_knowledge.txt."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("JNTU-GV COLLEGE KNOWLEDGE BASE\n")
        f.write("Auto-generated by scrape_college.py\n")
        f.write(f"Total entries: {len(entries)}\n")
        f.write("=" * 80 + "\n\n")

        for entry in entries:
            f.write("─" * 60 + "\n")
            f.write(f"CATEGORY : {entry['category']}\n")
            f.write(f"TITLE    : {entry['label']}\n")
            f.write(f"SOURCE   : {entry['url']}\n")
            f.write("─" * 60 + "\n")
            f.write(entry["content"])
            f.write("\n")

            if entry.get("links"):
                # Write unique document/PDF links found on the page
                seen_links: set[str] = set()
                pdf_lines  = []
                for lnk in entry["links"]:
                    if lnk not in seen_links:
                        seen_links.add(lnk)
                        if lnk.lower().endswith(".pdf"):
                            pdf_lines.append(f"  PDF: {lnk}")
                if pdf_lines:
                    f.write("\n[DOCUMENT LINKS FOUND ON THIS PAGE]\n")
                    f.write("\n".join(pdf_lines))
                    f.write("\n")

            f.write("\n\n")

    print(f"\n✓ Knowledge file saved → {output_path}")
    print(f"  Size: {os.path.getsize(output_path):,} bytes")


# ──────────────────────────────────────────────────────────────────────────────
# RAG integration — load scraped entries into the FAISS vector index
# ──────────────────────────────────────────────────────────────────────────────

def load_into_rag(entries: list[dict]) -> None:
    """
    Push all scraped entries into the RAG engine used by the chatbot.
    Each entry becomes one or more searchable document chunks.
    """
    print("\n─" * 40)
    print("Loading scraped content into RAG vector index …")

    # Import the RAG engine from the same project
    try:
        from rag import rag_engine
    except ImportError:
        print("  [ERROR] Cannot import rag.py — make sure you run this from the project folder.")
        return

    loaded = 0
    skipped = 0

    for entry in entries:
        content = entry["content"].strip()
        if not content:
            skipped += 1
            continue

        title   = entry["title"]
        url     = entry["url"]
        category = entry["category"]

        # Split large pages into ~1000-char chunks so retrieval stays precise
        chunks = _chunk_text(content, chunk_size=1000, overlap=100)

        for i, chunk in enumerate(chunks):
            chunk_title = title if len(chunks) == 1 else f"{title} [part {i+1}/{len(chunks)}]"
            # Append source URL at the end of each chunk so the LLM can cite it
            chunk_with_url = f"{chunk}\n\nSource: {url}"

            try:
                rag_engine.add_document(
                    title     = chunk_title,
                    content   = chunk_with_url,
                    source    = "scrape_college",
                    added_by  = "auto_scraper",
                )
                loaded += 1
            except Exception as e:
                print(f"  [RAG error] {chunk_title}: {e}")
                skipped += 1

    print(f"  ✓ Loaded {loaded} chunks into RAG index")
    if skipped:
        print(f"  ✗ Skipped {skipped} entries")
    print(f"  Total documents in index: {rag_engine.doc_count}")


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """
    Split text into overlapping chunks of ~chunk_size characters.
    Splits on newlines where possible to keep sentences intact.
    """
    lines  = text.splitlines()
    chunks = []
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > chunk_size and current:
            chunks.append("\n".join(current))
            # Keep last few lines as overlap
            overlap_lines = []
            overlap_len   = 0
            for prev_line in reversed(current):
                overlap_len += len(prev_line) + 1
                overlap_lines.insert(0, prev_line)
                if overlap_len >= overlap:
                    break
            current     = overlap_lines
            current_len = overlap_len
        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return [c.strip() for c in chunks if c.strip()]


# ──────────────────────────────────────────────────────────────────────────────
# Knowledge file search (used by chatbot fallback)
# ──────────────────────────────────────────────────────────────────────────────

def search_knowledge_file(query: str, top_k: int = 5) -> list[dict]:
    """
    Simple keyword search over college_knowledge.txt.
    Used as a fallback when RAG vector search is unavailable.

    Returns list of {"title", "url", "snippet"} sorted by relevance.
    """
    if not os.path.exists(OUTPUT_FILE):
        return []

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split into entries by the separator
    sections = raw.split("─" * 60)
    results  = []

    query_words = set(re.sub(r"[^\w\s]", "", query.lower()).split())
    stop = {"the", "a", "an", "of", "in", "for", "and", "to", "is", "are",
            "what", "how", "when", "where", "which", "tell", "me", "about"}
    query_words -= stop

    for section in sections:
        if not section.strip():
            continue

        # Extract metadata
        title_m  = re.search(r"TITLE\s*:\s*(.+)", section)
        source_m = re.search(r"SOURCE\s*:\s*(.+)", section)
        title    = title_m.group(1).strip()  if title_m  else "Unknown"
        source   = source_m.group(1).strip() if source_m else ""

        # Score by keyword overlap
        section_words = set(re.sub(r"[^\w\s]", "", section.lower()).split())
        matches = query_words & section_words
        if not matches:
            continue
        score = len(matches) / max(len(query_words), 1)

        # Extract a relevant snippet (first 400 chars after the metadata header)
        body_start = section.find("\n", section.find("SOURCE"))
        snippet    = section[body_start:body_start + 400].strip() if body_start > 0 else section[:400]

        results.append({
            "title":   title,
            "url":     source,
            "snippet": snippet,
            "_score":  score,
        })

    results.sort(key=lambda x: x["_score"], reverse=True)
    return results[:top_k]


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape JNTU-GV website and build chatbot knowledge base."
    )
    parser.add_argument(
        "--txt-only",
        action="store_true",
        help="Save to college_knowledge.txt only — skip loading into RAG",
    )
    parser.add_argument(
        "--rag-only",
        action="store_true",
        help="Skip scraping — reload college_knowledge.txt into RAG only",
    )
    args = parser.parse_args()

    # ── Option: reload existing file into RAG without re-scraping ────────────
    if args.rag_only:
        if not os.path.exists(OUTPUT_FILE):
            print(f"[ERROR] {OUTPUT_FILE} not found. Run without --rag-only first.")
            sys.exit(1)
        print(f"Re-loading {OUTPUT_FILE} into RAG …")
        entries = _parse_knowledge_file(OUTPUT_FILE)
        load_into_rag(entries)
        return

    # ── Scrape all sources ───────────────────────────────────────────────────
    print("=" * 60)
    print("JNTU-GV Knowledge Base Builder")
    print(f"Scraping {len(SOURCES)} sources …")
    print("=" * 60)

    entries: list[dict] = []
    failed:  list[str]  = []

    for i, source in enumerate(SOURCES, 1):
        print(f"\n[{i}/{len(SOURCES)}]", end="")
        try:
            result = scrape_source(source)
            if result:
                entries.append(result)
            else:
                failed.append(source["url"])
        except Exception:
            print(f"  [UNEXPECTED ERROR]")
            traceback.print_exc()
            failed.append(source["url"])

        # Polite delay
        if i < len(SOURCES):
            time.sleep(REQUEST_DELAY)

    # ── Write knowledge file ─────────────────────────────────────────────────
    if entries:
        write_knowledge_file(entries, OUTPUT_FILE)
    else:
        print("\n[WARNING] No entries were scraped. college_knowledge.txt not written.")

    # ── Load into RAG ────────────────────────────────────────────────────────
    if entries and not args.txt_only:
        load_into_rag(entries)

    # ── Summary ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Sources attempted : {len(SOURCES)}")
    print(f"  Successfully scraped : {len(entries)}")
    print(f"  Failed / skipped    : {len(failed)}")
    if failed:
        print("\n  Failed URLs:")
        for u in failed:
            print(f"    ✗ {u}")
    print(f"\n  Output file : {OUTPUT_FILE}")
    if not args.txt_only and entries:
        print("  RAG index   : updated")
    print("=" * 60)


def _parse_knowledge_file(path: str) -> list[dict]:
    """Parse an existing college_knowledge.txt back into entry dicts (for --rag-only)."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    sections = raw.split("─" * 60)
    entries  = []
    for section in sections:
        title_m    = re.search(r"TITLE\s*:\s*(.+)", section)
        source_m   = re.search(r"SOURCE\s*:\s*(.+)", section)
        category_m = re.search(r"CATEGORY\s*:\s*(.+)", section)
        if not title_m:
            continue
        # Content is everything after the metadata block
        body_match = re.search(r"SOURCE\s*:.+\n([\s\S]+)", section)
        content    = body_match.group(1).strip() if body_match else section.strip()
        entries.append({
            "title":    title_m.group(1).strip()    if title_m    else "Unknown",
            "url":      source_m.group(1).strip()   if source_m   else "",
            "category": category_m.group(1).strip() if category_m else "General",
            "label":    title_m.group(1).strip()    if title_m    else "Unknown",
            "content":  content[:MAX_CONTENT_CHARS],
            "links":    [],
        })
    return entries


if __name__ == "__main__":
    main()
