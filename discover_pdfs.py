# -*- coding: utf-8 -*-
"""
discover_pdfs.py
────────────────
Crawls the official JNTU-GV College of Engineering website and
discovers every PDF link, without downloading any file.

Output: pdf_links.csv
Columns: Title, URL, Category, Date

Usage:
    python discover_pdfs.py              # full crawl
    python discover_pdfs.py --depth 2    # limit crawl depth (default: 3)
    python discover_pdfs.py --no-crawl   # only seed pages, no following links
"""

import re
import csv
import sys
import time
import argparse
from collections import deque
from datetime import datetime
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────────────────
# Allowed domains  — never leave these
# ─────────────────────────────────────────────────────────────────────────────
ALLOWED_DOMAINS = {
    "jntugvcev.edu.in",
    "www.jntugvcev.edu.in",
    "jntugv.edu.in",
    "www.jntugv.edu.in",
}

# ─────────────────────────────────────────────────────────────────────────────
# Seed pages — every page known from the project that may contain PDFs
# ─────────────────────────────────────────────────────────────────────────────
SEED_PAGES = [
    # Core
    "https://jntugvcev.edu.in/",
    "https://www.jntugv.edu.in/",
    "https://jntugvcev.edu.in/notifications/",
    "https://jntugvcev.edu.in/circulars/",

    # Academics
    "https://jntugvcev.edu.in/academics/courses-offered/",
    "https://jntugvcev.edu.in/academics/admissions/admission-procedure/",
    "https://jntugvcev.edu.in/academics/admissions/fee-structure/",

    # Examinations
    "https://jntugvcev.edu.in/academics/examinations/results/",
    "https://jntugvcev.edu.in/academics/examinations/examination-time-tables/",
    "https://jntugvcev.edu.in/academics/regulations/",
    "https://jntugvcev.edu.in/academics/academic-calendar/",
    "https://jntugvcev.edu.in/academics/syllabus/",

    # Departments
    "https://jntugvcev.edu.in/departments/cse/",
    "https://jntugvcev.edu.in/departments/ece/",
    "https://jntugvcev.edu.in/departments/eee/",
    "https://jntugvcev.edu.in/departments/mechanical/",
    "https://jntugvcev.edu.in/departments/civil/",

    # Placements / facilities / student
    "https://jntugvcev.edu.in/beta/placements/training-placements-cell/",
    "https://jntugvcev.edu.in/facilities/hostels/",
    "https://jntugvcev.edu.in/facilities/library/",
    "https://jntugvcev.edu.in/rd-cell/about-research/",
    "https://jntugvcev.edu.in/student-corner/nss/",
    "https://jntugvcev.edu.in/admistration/",
    "https://jntugvcev.edu.in/contact-us/telephone-directory/",
    "https://jntugvcev.edu.in/gallery/",
]

# ─────────────────────────────────────────────────────────────────────────────
# Category classification rules
# Each entry: (regex_pattern, category_label)
# Checked against "link text + URL" combined, first match wins.
# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_RULES = [
    # Timetables
    (r"time[\s\-]?table|mid[\s\-]?exam|end[\s\-]?exam|examination[\s\-]schedule"
     r"|exam[\s\-]?date|i[\s\-]mid|ii[\s\-]mid|i[\s\-]sem|ii[\s\-]sem"
     r"|iii[\s\-]sem|iv[\s\-]sem|v[\s\-]sem|vi[\s\-]sem|vii[\s\-]sem|viii[\s\-]sem",
     "Timetables"),

    # Notifications / circulars
    (r"notification|circular|postpone|revalue|revaluation|recounting"
     r"|special[\s\-]?suppl|advanced[\s\-]?suppl",
     "Notifications"),

    # Results
    (r"result|merit[\s\-]?list|rank[\s\-]?list|pass[\s\-]?list",
     "Results"),

    # Syllabus
    (r"syllabus|syllabi|course[\s\-]?structure|course[\s\-]?plan|curriculum",
     "Syllabus"),

    # Regulations
    (r"regulation|r\d{2}[\s\-]?regulation|academic[\s\-]?rule|ordinance|statute",
     "Regulations"),

    # Academic Calendar
    (r"academic[\s\-]?calendar|calendar[\s\-]?\d{4}|schedule[\s\-]?\d{4}"
     r"|almanac|important[\s\-]?date",
     "Academic Calendar"),

    # Fee Structure
    (r"fee[\s\-]?structure|fee[\s\-]?detail|tuition[\s\-]?fee|hostel[\s\-]?fee"
     r"|admission[\s\-]?fee|fee[\s\-]?reimbursement",
     "Fee Structure"),

    # Admissions
    (r"admission|prospectus|eligibility|counselling|counseling|eamcet|eapcet|icet|pgecet",
     "Admissions"),

    # Placements
    (r"placement|recruiter|offer[\s\-]?letter|campus[\s\-]?drive|internship",
     "Placements"),

    # Hostel
    (r"hostel|accommodation|mess|boarding",
     "Hostel"),

    # Academics (general fallback for department / course pages)
    (r"academic|department|cse|ece|eee|mech|civil|mca|mba|m\.tech|b\.tech"
     r"|course|programme|program|btech|mtech",
     "Academics"),
]
_COMPILED_RULES = [(re.compile(p, re.I), cat) for p, cat in CATEGORY_RULES]


# ─────────────────────────────────────────────────────────────────────────────
# Date extraction
# ─────────────────────────────────────────────────────────────────────────────

# Months for pattern matching
_MONTHS = (r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
           r"|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?")

_DATE_PATTERNS = [
    # "March-2026", "November/December-2025", "May/June-2024"
    re.compile(
        rf"(?:{_MONTHS})[\s/\-]+(?:{_MONTHS})?[\s/\-]*(\d{{4}})",
        re.I
    ),
    # "2026-03", "2025-11"
    re.compile(r"\b(20\d{2})[\-/]\d{1,2}\b"),
    # "March 2026", "Nov 2025"
    re.compile(rf"(?:{_MONTHS})\s+(\d{{4}})", re.I),
    # Bare year near the title: last 4-digit year found
    re.compile(r"\b(20\d{2})\b"),
]


def extract_date(text: str) -> str:
    """Return the best date string found in text, or '' if none."""
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if m:
            # Return the whole match (not just the year group) when it contains a month
            full = m.group(0).strip()
            return full
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Category classification
# ─────────────────────────────────────────────────────────────────────────────

def classify(title: str, url: str) -> str:
    """Return the most appropriate category for a PDF link."""
    combined = f"{title} {url}"
    for pattern, category in _COMPILED_RULES:
        if pattern.search(combined):
            return category
    return "General"


# ─────────────────────────────────────────────────────────────────────────────
# URL helpers
# ─────────────────────────────────────────────────────────────────────────────

def _in_scope(url: str) -> bool:
    """Return True if URL is within the allowed JNTU-GV domains."""
    try:
        host = urlparse(url).netloc.lstrip("www.")
        return any(host == d.lstrip("www.") for d in ALLOWED_DOMAINS)
    except Exception:
        return False


def _normalise(url: str) -> str:
    """Remove fragment, trailing slash variation."""
    url, _ = urldefrag(url)
    return url.rstrip("/")


def _is_pdf(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".pdf")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 15


def _get(url: str) -> requests.Response | None:
    """HEAD + GET with graceful error handling. Returns None on failure."""
    try:
        # HEAD first — only follow up with GET for HTML pages
        head = requests.head(url, headers=HEADERS, timeout=8,
                             allow_redirects=True)
        ct = head.headers.get("Content-Type", "")
        if "html" not in ct and "text" not in ct:
            return None   # skip non-HTML (binary, PDF, etc.)
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                         allow_redirects=True)
        r.raise_for_status()
        return r
    except requests.RequestException:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Link extraction from a single page
# ─────────────────────────────────────────────────────────────────────────────

def extract_links_from_page(html: str, page_url: str) -> tuple[list[dict], list[str]]:
    """
    Parse an HTML page and return:
      pdf_entries  — list of PDF dicts ready for the CSV
      follow_urls  — in-scope HTML page URLs to crawl next
    """
    soup       = BeautifulSoup(html, "html.parser")
    pdf_entries: list[dict] = []
    follow_urls: list[str]  = []

    for a in soup.find_all("a", href=True):
        raw_href = a["href"].strip()
        if not raw_href or raw_href.startswith("mailto:") or raw_href.startswith("tel:"):
            continue

        abs_url = urljoin(page_url, raw_href)
        norm    = _normalise(abs_url)

        if not _in_scope(norm):
            continue

        if _is_pdf(norm):
            # Get link text + surrounding context for title / date
            link_text   = a.get_text(" ", strip=True)
            parent_text = ""
            if a.parent:
                parent_text = a.parent.get_text(" ", strip=True)[:200]
            combined_text = f"{link_text} {parent_text}"

            # Title: prefer link text; fall back to filename from URL
            if link_text and len(link_text) > 5:
                title = re.sub(r"\s+", " ", link_text).strip()
            else:
                filename = urlparse(norm).path.split("/")[-1]
                # Un-slugify: replace hyphens/underscores, strip .pdf
                title = re.sub(r"[-_]+", " ",
                               filename.replace(".pdf", "")).strip().title()

            date     = extract_date(combined_text)
            category = classify(title, norm)

            pdf_entries.append({
                "Title":    title,
                "URL":      norm,
                "Category": category,
                "Date":     date,
            })

        else:
            # Only follow HTML pages within scope
            follow_urls.append(norm)

    return pdf_entries, follow_urls


# ─────────────────────────────────────────────────────────────────────────────
# BFS crawler
# ─────────────────────────────────────────────────────────────────────────────

def crawl(seed_pages: list[str], max_depth: int = 3,
          follow_links: bool = True, delay: float = 1.0) -> list[dict]:
    """
    BFS crawl starting from seed_pages.
    Returns deduplicated list of PDF entry dicts.
    """
    visited_pages: set[str] = set()
    seen_pdfs:     set[str] = set()
    all_pdfs:      list[dict] = []

    # Queue items: (url, depth)
    queue: deque[tuple[str, int]] = deque()
    for url in seed_pages:
        queue.append((_normalise(url), 0))
        visited_pages.add(_normalise(url))

    pages_crawled = 0
    total = len(queue)

    while queue:
        page_url, depth = queue.popleft()
        pages_crawled  += 1

        print(f"  [{pages_crawled}] depth={depth}  {page_url}")

        resp = _get(page_url)
        if resp is None:
            continue

        enc  = resp.encoding or "utf-8"
        html = resp.content.decode(enc, errors="replace")

        pdfs, follow = extract_links_from_page(html, page_url)

        # Collect new PDFs
        for entry in pdfs:
            if entry["URL"] not in seen_pdfs:
                seen_pdfs.add(entry["URL"])
                all_pdfs.append(entry)
                print(f"      ✓ PDF [{entry['Category']}]  {entry['Title'][:60]}")

        # Enqueue new HTML pages
        if follow_links and depth < max_depth:
            for next_url in follow:
                if next_url not in visited_pages:
                    visited_pages.add(next_url)
                    queue.append((next_url, depth + 1))
                    total += 1

        print(f"      PDFs found so far: {len(all_pdfs)} | Pages queued: {len(queue)}")

        if queue:
            time.sleep(delay)

    return all_pdfs


# ─────────────────────────────────────────────────────────────────────────────
# CSV writer
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_CSV = "pdf_links.csv"
FIELDNAMES = ["Title", "URL", "Category", "Date"]


def save_csv(entries: list[dict], path: str = OUTPUT_CSV) -> None:
    """Write entries to CSV, sorted by Category then Title."""
    entries_sorted = sorted(entries, key=lambda x: (x["Category"], x["Title"].lower()))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES,
                                extrasaction="ignore", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(entries_sorted)

    # Category summary
    from collections import Counter
    counts = Counter(e["Category"] for e in entries_sorted)
    print(f"\n✓ Saved {path}  ({len(entries_sorted)} PDFs)")
    print("\n  Category breakdown:")
    for cat, count in sorted(counts.items()):
        print(f"    {cat:<22} {count:>4} PDF(s)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover PDF links on the JNTU-GV College website."
    )
    parser.add_argument(
        "--depth", type=int, default=3,
        help="Maximum crawl depth from each seed page (default: 3)"
    )
    parser.add_argument(
        "--no-crawl", action="store_true",
        help="Only scan seed pages — do not follow any links"
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Pause between HTTP requests in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--output", type=str, default=OUTPUT_CSV,
        help=f"Output CSV file path (default: {OUTPUT_CSV})"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("JNTU-GV PDF Discoverer")
    print(f"Seed pages  : {len(SEED_PAGES)}")
    print(f"Max depth   : {args.depth if not args.no_crawl else 'seed-only'}")
    print(f"Output file : {args.output}")
    print(f"Started at  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    try:
        pdfs = crawl(
            seed_pages   = SEED_PAGES,
            max_depth    = args.depth,
            follow_links = not args.no_crawl,
            delay        = args.delay,
        )
    except KeyboardInterrupt:
        print("\n[Interrupted] Saving results collected so far …")
        pdfs = []   # will be empty; let the save handle it gracefully

    if not pdfs:
        print("\nNo PDF links found.")
        print("This is expected if the site is a JavaScript SPA (React/Vue) —")
        print("PDF hrefs are injected by JS at runtime and not visible in static HTML.")
        print("\nTip: Add direct PDF URLs manually to the SEED_PAGES list,")
        print("     or use the browser DevTools → Network tab to capture them.")
        sys.exit(0)

    save_csv(pdfs, args.output)

    print(f"\nFinished at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
