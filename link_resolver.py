# -*- coding: utf-8 -*-
"""
link_resolver.py — Real-time, recency-aware document resolver for JNTU-GV.

Key improvements over v1:
  - Recency-first: scores and filters by year (prefers 2024/2025/2026).
  - Course structure validation: MCA has 4 sems, M.Tech has 4, B.Tech has 8, etc.
  - Semester normalisation: converts "2nd year" → "II-Semester", "3rd year" → "V/VI-Semester".
  - Returns NO results (with a clear message) when only outdated docs match.
  - Distinguishes timetable vs notification vs result vs circular.
  - Tries the live API first, then the HTML page, then admits failure honestly.
"""

import re
import urllib.request
import json
from difflib import SequenceMatcher
from datetime import datetime


# ──────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10

CURRENT_YEAR = datetime.now().year            # e.g. 2026
RECENT_YEARS = {str(y) for y in range(CURRENT_YEAR - 1, CURRENT_YEAR + 2)}  # 2025-2027
STALE_CUTOFF = CURRENT_YEAR - 3              # anything older than 3 years = stale

BASE_URL      = "https://jntugvcev.edu.in"
BASE_URL_UNIV = "https://jntugv.edu.in"

# Live JSON API — all notifications/timetables come from here
NOTIFICATION_API = "https://api.jntugvcev.edu.in/api/updates/allnotifications"
CIRCULAR_API     = "https://api.jntugvcev.edu.in/api/updates/allcirculars"

# Fallback static pages — prefer jntugv.edu.in for results/regulations
PAGE_URLS = {
    "timetables":    f"{BASE_URL}/academics/examinations/examination-time-tables/",
    "notifications": f"{BASE_URL}/notifications/",
    "results":       f"{BASE_URL_UNIV}/results",
    "circulars":     f"{BASE_URL}/circulars/",
    "regulations":   f"{BASE_URL_UNIV}/regulations",
    "examinations":  f"{BASE_URL_UNIV}/examination",
}

# ── Course structure: max valid semesters per programme ──
COURSE_SEMESTERS = {
    "btech":    8,   # B.Tech — 4 years × 2 semesters
    "b.tech":   8,
    "mtech":    4,   # M.Tech — 2 years × 2 semesters
    "m.tech":   4,
    "mca":      4,   # MCA (revised 2-year) — 4 semesters
    "mba":      4,   # MBA — 2 years × 2 semesters
    "bpharm":   8,   # B.Pharmacy — 4 years × 2 semesters
    "b.pharm":  8,
    "mpharm":   4,   # M.Pharmacy — 2 years × 2 semesters
    "m.pharm":  4,
    "pharmd":   12,  # Pharm.D — 6 years × 2 semesters
}

# Roman numeral → integer for semester validation
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6,
         "vii": 7, "viii": 8, "ix": 9, "x": 10}


# ──────────────────────────────────────────────────────────
# HTTP
# ──────────────────────────────────────────────────────────

def _fetch(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[LinkResolver] fetch error {url}: {e}")
        return None


# ──────────────────────────────────────────────────────────
# Course structure validation
# ──────────────────────────────────────────────────────────

def _detect_programme(text: str) -> str | None:
    """Return the programme key if one is mentioned in text."""
    t = text.lower()
    for key in sorted(COURSE_SEMESTERS, key=len, reverse=True):
        if key in t:
            return key
    return None


def _extract_semester_number(text: str) -> int | None:
    """Extract semester number from a string. Returns integer or None."""
    t = text.lower()
    # Arabic: "3rd semester", "semester 3", "3 semester"
    m = re.search(r'(\d+)\s*(?:st|nd|rd|th)?\s*sem', t)
    if m:
        return int(m.group(1))
    m = re.search(r'sem(?:ester)?\s*(\d+)', t)
    if m:
        return int(m.group(1))
    # Roman: "II-Semester", "III Semester"
    m = re.search(r'\b(i{1,3}|iv|v|vi|vii|viii|ix|x)\b[\s\-]*sem', t)
    if m:
        val = ROMAN.get(m.group(1))
        return val if val is not None else None
    m = re.search(r'sem[\s\-]*(i{1,3}|iv|v|vi|vii|viii|ix|x)\b', t)
    if m:
        val = ROMAN.get(m.group(1))
        return val if val is not None else None
    # Year → semester: "2nd year" = sem 3 or 4
    m = re.search(r'(\d+)\s*(?:st|nd|rd|th)\s*year', t)
    if m:
        yr = int(m.group(1))
        return (yr - 1) * 2 + 1   # return first semester of that year
    return None


def validate_semester(query: str, doc_title: str) -> bool:
    """
    Return False if the document title contains a semester that is
    structurally impossible for the programme mentioned in the query.
    """
    programme = _detect_programme(query)
    if not programme:
        return True   # no programme context — allow through

    max_sem = COURSE_SEMESTERS[programme]
    doc_sem = _extract_semester_number(doc_title)

    # doc_sem can be None if no semester was found — allow through
    if doc_sem is not None and isinstance(doc_sem, int) and doc_sem > max_sem:
        print(f"[LinkResolver] INVALID: '{doc_title}' → sem {doc_sem} > max {max_sem} for {programme}")
        return False
    return True


# ──────────────────────────────────────────────────────────
# Year / recency helpers
# ──────────────────────────────────────────────────────────

def _extract_years(text: str) -> list[int]:
    """Return all 4-digit years found in text."""
    return [int(y) for y in re.findall(r'\b(20\d{2})\b', text)]


def _recency_score(title: str) -> float:
    """
    Score 0–1 based on how recent the document is.
    Documents from the current year or last year score highest.
    Documents older than STALE_CUTOFF score 0.
    """
    years = _extract_years(title)
    if not years:
        # No year in title — treat as moderate age (might be recent)
        return 0.3
    latest = max(years)
    if latest >= CURRENT_YEAR:
        return 1.0
    if latest == CURRENT_YEAR - 1:
        return 0.85
    if latest == CURRENT_YEAR - 2:
        return 0.50
    if latest <= STALE_CUTOFF:
        return 0.0   # explicitly stale — will be filtered out
    return 0.2


def _is_stale(title: str) -> bool:
    years = _extract_years(title)
    if not years:
        return False   # unknown age — keep
    return max(years) <= STALE_CUTOFF


# ──────────────────────────────────────────────────────────
# Parsers
# ──────────────────────────────────────────────────────────

def _parse_api_response(raw: str) -> list[dict]:
    docs = []
    try:
        data = json.loads(raw)
        items = data if isinstance(data, list) else (
            data.get("data") or data.get("notifications") or
            data.get("circulars") or []
        )
        for item in items:
            title = (
                item.get("title") or item.get("name") or
                item.get("subject") or item.get("heading") or ""
            ).strip()
            url = (
                item.get("link") or item.get("url") or
                item.get("file") or item.get("pdf") or
                item.get("attachment") or ""
            ).strip()
            if title:
                if url and url.startswith("/"):
                    url = BASE_URL + url
                docs.append({"title": title, "url": url})
    except Exception as e:
        print(f"[LinkResolver] JSON parse error: {e}")
    return docs


def _parse_html_links(html: str) -> list[dict]:
    """Extract document links from static HTML (SPA fallback)."""
    docs = []
    pattern = re.compile(
        r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )
    for m in pattern.finditer(html):
        href = m.group(1).strip()
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if not title or len(title) < 10:
            continue
        # Keep only document-like hrefs
        if not any(x in href.lower() for x in
                   [".pdf", ".doc", "download", "file", "notification",
                    "timetable", "result", "circular"]):
            continue
        if href.startswith("/"):
            href = BASE_URL + href
        docs.append({"title": title, "url": href})

    # React SPAs often render text nodes without <a> tags for PDFs.
    # Also extract plain text titles that look like timetable/notification entries
    # so we can at least show the title even if the URL is missing.
    text_only = re.findall(
        r'(?:Timetable|Notification|Result|Circular)[^<\n]{10,120}',
        html, re.IGNORECASE
    )
    seen = {d["title"].lower() for d in docs}
    for t in text_only:
        t = t.strip()
        if t.lower() not in seen and len(t) > 15:
            docs.append({"title": t, "url": ""})
            seen.add(t.lower())

    return docs


# ──────────────────────────────────────────────────────────
# Scoring & ranking
# ──────────────────────────────────────────────────────────

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# Normalise query terms before matching
_QUERY_NORMALISE = {
    "1st year": "i-semester",  "first year":  "i-semester",
    "2nd year": "iii-semester","second year": "iii-semester",
    "3rd year": "v-semester",  "third year":  "v-semester",
    "4th year": "vii-semester","fourth year": "vii-semester",
    "1 year":   "i-semester",  "2 year":      "iii-semester",
    "3 year":   "v-semester",  "4 year":      "vii-semester",
    "supply":   "supplementary",
    "supp":     "supplementary",
    "mid-1":    "mid",         "mid 1": "mid",
    "mid-2":    "mid",         "mid 2": "mid",
}

def _normalise(text: str) -> str:
    t = text.lower()
    for src, dst in _QUERY_NORMALISE.items():
        t = t.replace(src, dst)
    return t


def _score(query: str, title: str) -> float:
    """
    Combined relevance score: keyword overlap + recency + fuzzy similarity.
    Recency is weighted heavily to prevent old docs from ranking high.
    """
    nq = _normalise(query)
    nt = _normalise(title)

    q_words = set(re.sub(r"[^\w]", " ", nq).split())
    t_words = set(re.sub(r"[^\w]", " ", nt).split())

    stop = {"for", "the", "of", "and", "in", "a", "an", "to", "at", "on",
            "is", "are", "was", "be", "with", "from", "by", "&"}
    q_words -= stop
    t_words -= stop

    if not q_words:
        return 0.0

    matches  = q_words & t_words
    overlap  = len(matches) / len(q_words)

    # Extra weight for important domain tokens
    high_value = {
        "btech", "mtech", "mca", "mba", "bpharm", "mpharm",
        "timetable", "notification", "result", "circular",
        "regular", "supplementary", "mid", "end",
        "i", "ii", "iii", "iv", "v", "vi", "vii", "viii",
        "r19", "r22", "r25", "r17", "r16", "r13",
        str(CURRENT_YEAR), str(CURRENT_YEAR - 1), str(CURRENT_YEAR + 1)
    }
    bonus = sum(0.10 for w in matches if w in high_value)

    relevance = min(1.0, overlap + bonus + _similarity(nq, nt) * 0.25)
    recency   = _recency_score(title)

    # Final score: 60% relevance + 40% recency
    return relevance * 0.60 + recency * 0.40


def _rank(query: str, docs: list[dict], top_k: int = 5) -> list[dict]:
    """Score, validate semester, filter stale, rank, return top_k."""
    scored = []
    for doc in docs:
        title = doc["title"]

        # Hard filter 1: structurally impossible semester
        if not validate_semester(query, title):
            continue

        # Hard filter 2: stale document (> 3 years old)
        if _is_stale(title):
            continue

        s = _score(query, title)
        if s > 0.12:
            scored.append({**doc, "_score": round(s, 4)})

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored[:top_k]


# ──────────────────────────────────────────────────────────
# Category detection
# ──────────────────────────────────────────────────────────

def _detect_category(query: str) -> str:
    q = query.lower()
    if any(w in q for w in ["timetable", "time table", "schedule",
                             "exam date", "exam time", "when is exam"]):
        return "timetables"
    if any(w in q for w in ["result", "marks", "grade", "cgpa",
                             "pass", "fail", "score"]):
        return "results"
    if any(w in q for w in ["circular"]):
        return "circulars"
    return "notifications"   # covers timetables + general notices


# ──────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────

def resolve_links(query: str, top_k: int = 5) -> dict:
    """
    Resolve the best matching live documents for the user's query.

    Returns a dict:
    {
        "status":  "ok" | "no_results" | "stale_only" | "unavailable",
        "docs":    [...],   # list of {"title", "url", "_score"}
        "message": str      # human-readable status message for the bot
    }
    """
    category = _detect_category(query)
    raw_docs: list[dict] = []

    # ── Try API first ──────────────────────────────────────
    api_url = CIRCULAR_API if category == "circulars" else NOTIFICATION_API
    raw = _fetch(api_url)
    if raw and raw.strip().startswith(("[", "{")):
        raw_docs = _parse_api_response(raw)
        print(f"[LinkResolver] API → {len(raw_docs)} docs")

    # ── Fallback: HTML page ────────────────────────────────
    if not raw_docs:
        page_url = PAGE_URLS.get(category)
        if page_url:
            html = _fetch(page_url)
            if html:
                raw_docs = _parse_html_links(html)
                print(f"[LinkResolver] HTML → {len(raw_docs)} docs")

    # ── Nothing fetched at all ─────────────────────────────
    if not raw_docs:
        return {
            "status":  "unavailable",
            "docs":    [],
            "message": (
                "I was unable to reach the JNTU-GV website right now. "
                "Please check directly at: "
                f"{PAGE_URLS.get(category, BASE_URL)}"
            )
        }

    # ── Rank with recency + validity filters ───────────────
    results = _rank(query, raw_docs, top_k=top_k)

    if results:
        return {"status": "ok", "docs": results, "message": ""}

    # ── Check whether stale docs exist for this query ──────
    # (Run ranking again without the stale filter to see if old docs matched)
    stale_check = []
    for doc in raw_docs:
        if not validate_semester(query, doc["title"]):
            continue
        s = _score(query, doc["title"])
        if s > 0.12:
            stale_check.append(doc)

    if stale_check:
        return {
            "status":  "stale_only",
            "docs":    [],
            "message": (
                "I found matching documents, but they are from "
                f"{STALE_CUTOFF} or earlier and are likely outdated. "
                "The latest timetable or notification for your query "
                "has not been published on the website yet, or may be "
                "uploaded soon. Please check directly: "
                f"{PAGE_URLS.get(category, BASE_URL)}"
            )
        }

    return {
        "status":  "no_results",
        "docs":    [],
        "message": (
            "No matching timetable or notification was found for your query. "
            "This could mean it has not been published yet. "
            "Please check the official page for updates: "
            f"{PAGE_URLS.get(category, BASE_URL)}"
        )
    }


def format_links_for_bot(query: str) -> str:
    """
    Convenience wrapper used by app.py.
    Returns formatted HTML string (or status message) for the chatbot.
    """
    result = resolve_links(query)

    if result["status"] == "ok":
        lines = []
        for i, doc in enumerate(result["docs"], 1):
            title = doc["title"]
            url   = doc.get("url", "")
            if url:
                lines.append(
                    f'{i}. <a href="{url}" target="_blank" '
                    f'class="chat-link" rel="noopener noreferrer">{title}</a>'
                )
            else:
                lines.append(f"{i}. {title} <em>(direct link not available)</em>")
        return "<br>".join(lines)

    # For all non-ok statuses, return the honest message
    return result["message"]


# ──────────────────────────────────────────────────────────
# PDF / page content extractor
# ──────────────────────────────────────────────────────────

def _extract_pdf_text(url: str) -> str:
    """
    Download a PDF and extract plain text from it.
    Returns extracted text or empty string on failure.
    Requires PyMuPDF (fitz). Silently skips if not installed.
    """
    if not url or not url.lower().endswith(".pdf"):
        return ""
    try:
        import fitz  # PyMuPDF
        raw = _fetch(url)
        if not raw:
            return ""
        import io
        pdf_bytes = raw.encode("latin-1", errors="replace")
        # _fetch decodes as utf-8 which corrupts binary — re-fetch as bytes
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            pdf_bytes = r.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text("text"))
        doc.close()
        text = "\n".join(pages).strip()
        # Limit to first 3000 chars to keep context size manageable
        return text[:3000] if text else ""
    except ImportError:
        return ""   # PyMuPDF not installed — skip silently
    except Exception as e:
        print(f"[LinkResolver] PDF extract error for {url}: {e}")
        return ""


def fetch_document_content(url: str) -> str:
    """
    Fetch and return readable text content from a URL.
    Handles both PDF and HTML pages.
    Returns plain text (no HTML tags), max ~3000 chars.
    """
    if not url:
        return ""

    if url.lower().endswith(".pdf"):
        return _extract_pdf_text(url)

    # HTML page — strip tags
    html = _fetch(url)
    if not html:
        return ""
    # Remove script/style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html,
                  flags=re.DOTALL | re.IGNORECASE)
    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:3000]
