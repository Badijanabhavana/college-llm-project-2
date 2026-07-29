# -*- coding: utf-8 -*-
"""
web_retriever.py  — PRIMARY knowledge source for the JNTU-GV chatbot.

Fetches the official JNTU-GV website live, extracts clean text,
and reads any relevant PDF found on the page.

GUARANTEE: Every public function ALWAYS returns a valid object.
           Nothing here ever returns None or raises to the caller.
"""

import re
import io
import time

# Use requests instead of urllib — reliable timeouts on Windows
try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from dataclasses import dataclass
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup, Comment
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


# ─────────────────────────────────────────────────────────────────────────────
# Page catalogue
# ─────────────────────────────────────────────────────────────────────────────
PAGE_CATALOGUE = [
    (("timetable", "time table", "exam schedule", "exam date",
      "mid exam", "end exam", "mid-1", "mid-2", "i mid", "ii mid"),
     "https://jntugvcev.edu.in/academics/examinations/examination-time-tables/",
     "Examination Timetables and Notifications"),

    (("result", "marks", "grade sheet", "pass list", "merit list",
      "revaluation", "recounting"),
     "https://jntugv.edu.in/results",
     "JNTU-GV Examination Results Portal"),

    (("notification", "circular", "postpone", "postponement"),
     "https://jntugvcev.edu.in/notifications/",
     "Official Notifications — CEV"),

    (("university notification", "jntugv notification",
      "university circular", "university exam notification"),
     "https://jntugv.edu.in/notifications",
     "JNTU-GV University Notifications"),

    (("syllabus", "syllabi", "course content", "course plan", "subject list"),
     "https://jntugvcev.edu.in/academics/syllabus/",
     "Syllabus"),

    (("regulation", "r19", "r22", "r25", "r17", "academic rule"),
     "https://jntugv.edu.in/regulations",
     "JNTU-GV Academic Regulations"),

    (("academic calendar", "calendar", "important dates", "holiday list"),
     "https://jntugvcev.edu.in/academics/academic-calendar/",
     "Academic Calendar"),

    (("fee structure", "fee detail", "tuition fee", "hostel fee",
      "admission fee", "fee reimbursement", "fee payment", "fees"),
     "https://jntugvcev.edu.in/academics/admissions/fee-structure/",
     "Fee Structure"),

    (("admission", "how to apply", "counselling", "counseling",
      "eamcet", "eapcet", "icet", "pgecet", "seat allotment",
      "documents required", "eligibility"),
     "https://jntugvcev.edu.in/academics/admissions/admission-procedure/",
     "Admission Procedure"),

    (("placement", "recruiter", "package", "lpa", "campus drive",
      "placed", "job offer", "internship"),
     "https://jntugvcev.edu.in/beta/placements/training-placements-cell/",
     "Training and Placements"),

    (("hostel", "accommodation", "mess", "boarding", "boys hostel", "girls hostel"),
     "https://jntugvcev.edu.in/facilities/hostels/",
     "Hostels"),

    (("library", "book", "journal", "e-resource"),
     "https://jntugvcev.edu.in/facilities/library/",
     "Central Library"),

    (("research", "phd", "ph.d", "r&d", "rd cell", "scholar", "thesis"),
     "https://jntugvcev.edu.in/rd-cell/about-research/",
     "R&D Cell – Research"),

    (("cse department", "computer science department", "cse faculty"),
     "https://jntugvcev.edu.in/departments/cse/",
     "CSE Department"),

    (("ece department", "electronics department", "ece faculty"),
     "https://jntugvcev.edu.in/departments/ece/",
     "ECE Department"),

    (("eee department", "electrical department", "eee faculty"),
     "https://jntugvcev.edu.in/departments/eee/",
     "EEE Department"),

    (("mechanical department", "mech department", "mechanical faculty"),
     "https://jntugvcev.edu.in/departments/mechanical/",
     "Mechanical Engineering Department"),

    (("civil department", "civil faculty"),
     "https://jntugvcev.edu.in/departments/civil/",
     "Civil Engineering Department"),

    (("it department", "information technology department", "it faculty",
      "it courses"),
     "https://jntugvcev.edu.in/departments/it/",
     "IT Department — Information Technology"),

    (("pharmacy", "b.pharmacy", "bpharm", "m.pharmacy", "pharmaceutical",
      "drug", "pharmacology"),
     "https://jntugvcev.edu.in/departments/pharmacy/",
     "Pharmacy Department"),

    (("b.tech", "btech", "m.tech", "mtech", "mba", "mca",
      "course", "courses", "courses offered", "programs", "branches", "courses available",
      "all courses", "what courses", "all programs", "all departments",
      "departments available", "list of departments", "list of courses",
      "what departments"),
     "https://jntugvcev.edu.in/academics/courses-offered/",
     "Courses Offered — All Programs and Departments"),

    (("contact", "phone", "address", "telephone", "email"),
     "https://jntugvcev.edu.in/contact-us/telephone-directory/",
     "Contact and Telephone Directory"),

    (("principal", "head of the institution", "head of college", "principal details"),
     "https://jntugvcev.edu.in/admistration/principal/",
     "Principal Profile"),

    (("vice principal", "vice-principal"),
     "https://jntugvcev.edu.in/admistration/vice-principal/",
     "Vice Principal Profile"),

    (("about", "jntu-gv", "jntugv", "college", "university",
      "history", "accreditation", "naac", "aicte"),
     "https://jntugvcev.edu.in/",
     "JNTU-GV College of Engineering – Home"),

    # ── University portal (jntugv.edu.in) ──────────────────────────────
    (("university academics", "jntugv academics", "university departments",
      "affiliated colleges", "university programs"),
     "https://jntugv.edu.in/academics",
     "JNTU-GV University Academics"),

    (("university admissions", "jntugv admissions", "university counseling"),
     "https://jntugv.edu.in/admissions",
     "JNTU-GV University Admissions"),

    (("examination branch", "university examination", "jntugv exam"),
     "https://jntugv.edu.in/examination",
     "JNTU-GV University Examination Branch"),
]

_PDF_STOP = {"the", "a", "an", "of", "in", "for", "and", "to", "is",
             "are", "at", "on", "be", "with", "from", "by", "&", "or"}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
_TIMEOUT = 10   # seconds — hard limit, works on Windows with requests

_DROP_TAGS = {"script", "style", "noscript", "nav", "header",
              "footer", "aside", "form", "iframe", "svg", "head"}
_NOISE = re.compile(
    r"nav|menu|footer|header|sidebar|breadcrumb|cookie|banner|"
    r"social|share|advertisement|widget|popup|modal|pagination", re.I)


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass — always fully initialised, never None
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class RetrievalResult:
    source_url: str  = ""
    title:      str  = ""
    page_text:  str  = ""
    pdf_url:    str  = ""
    pdf_title:  str  = ""
    pdf_text:   str  = ""
    found:      bool = False
    error:      str  = ""   # human-readable reason when found=False


# ─────────────────────────────────────────────────────────────────────────────
# HTTP — uses requests with hard timeout, never hangs
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Simple TTL page cache — makes retrieval a function of (query, cache window)
# instead of a function of live-network timing. This is the main fix for
# "same question, different answer/page" caused by transient timeouts or
# momentary differences in page markup (menus/ads/widgets) between requests.
# ─────────────────────────────────────────────────────────────────────────────
_PAGE_CACHE: dict[str, tuple[float, bytes]] = {}
_CACHE_TTL_SECONDS = 6 * 60 * 60   # 6 hours — long enough to kill flakiness,
                                    # short enough that real site updates still show up


def _get_bytes(url: str) -> bytes:
    """Fetch URL bytes, using a TTL cache. Returns b'' on any failure — never None, never raises."""
    if not _HAS_REQUESTS:
        return b""

    now = time.time()
    cached = _PAGE_CACHE.get(url)
    if cached is not None:
        ts, data = cached
        if now - ts < _CACHE_TTL_SECONDS:
            return data
        # stale — fall through and refresh

    try:
        resp = _requests.get(url, headers=_HEADERS, timeout=_TIMEOUT,
                             allow_redirects=True)
        resp.raise_for_status()
        content = resp.content or b""
        _PAGE_CACHE[url] = (now, content)
        return content
    except Exception as e:
        print(f"[WebRetriever] fetch error {url}: {e}")
        # If we have a stale cached copy, prefer it over nothing —
        # a slightly old official page is more consistent than a random miss.
        if cached is not None:
            print(f"[WebRetriever] serving stale cache for {url} after fetch error")
            return cached[1]
        return b""


def _get_text(url: str) -> str:
    """Fetch URL as UTF-8 text. Returns '' on failure — never None."""
    raw = _get_bytes(url)
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# HTML cleaning
# ─────────────────────────────────────────────────────────────────────────────

def _clean_html(html: str, base_url: str) -> tuple[str, list[dict], list[dict]]:
    """Return (clean_text, pdf_links, internal_links). Always returns valid tuple."""
    if not html or not _HAS_BS4:
        return "", [], []

    try:
        soup = BeautifulSoup(html, "html.parser")

        # Collect PDF and internal links BEFORE decomposing DOM (so we don't lose nav links)
        pdf_links = []
        internal_links = []
        for a in soup.find_all("a", href=True):
            try:
                href = (a.get("href") or "").strip()
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                abs_url = urljoin(base_url, href)
                
                # Extract link text for scoring
                link_text = a.get_text(" ", strip=True) or ""
                parent_text = ""
                if a.parent:
                    try:
                        parent_text = a.parent.get_text(" ", strip=True)[:120] or ""
                    except Exception:
                        pass
                title = link_text if len(link_text) > 5 else parent_text[:80]
                title = re.sub(r"\s+", " ", title).strip() or abs_url

                if abs_url.lower().endswith(".pdf"):
                    pdf_links.append({"title": title, "url": abs_url})
                elif "jntugv" in abs_url.lower() or href.startswith("/"):
                    internal_links.append({"title": title, "url": abs_url})
            except Exception:
                continue

        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            c.extract()
        for tag in soup.find_all(_DROP_TAGS):
            tag.decompose()

        # Extract clean text
        raw = soup.get_text(separator="\n") or ""
        lines = []
        prev_line = None
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # Keep consecutive deduplication only (to avoid huge spacing issues)
            # but stop global deduplication that destroys tables and headings
            if line == prev_line:
                continue
            prev_line = line
            lines.append(line)

        return "\n".join(lines), pdf_links, internal_links

    except Exception as e:
        print(f"[WebRetriever] HTML parse error: {e}")
        return "", [], []


# ─────────────────────────────────────────────────────────────────────────────
# PDF extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes. Always returns str, never None."""
    if not pdf_bytes:
        return ""
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                t = page.extract_text() or ""
                if t.strip():
                    pages.append(f"[Page {i}]\n{t.strip()}")
        text = "\n\n".join(pages)
        return text if text.strip() else ""
    except ImportError:
        pass
    except Exception as e:
        print(f"[WebRetriever] pdfplumber error: {e}")

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for i, page in enumerate(reader.pages, 1):
            t = page.extract_text() or ""
            if t.strip():
                pages.append(f"[Page {i}]\n{t.strip()}")
        text = "\n\n".join(pages)
        return text if text.strip() else ""
    except Exception as e:
        print(f"[WebRetriever] PyPDF2 error: {e}")

    return ""


# ─────────────────────────────────────────────────────────────────────────────
# PDF & Link relevance scoring
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_text(s: str) -> str:
    """Clean text by replacing punctuation/hyphens with spaces."""
    s = (s or "").lower()
    s = re.sub(r"[_\-/\\]", " ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def _extract_regulations(text: str) -> set[str]:
    """Extract regulation tags like R19, R20, R22, R23, R25 from text."""
    matches = re.findall(r"\br\d{2}\b", (text or "").lower())
    return set(matches)


def _extract_semesters(text: str) -> set[str]:
    """Extract semester and year indicators from text."""
    t = (text or "").lower()
    sems = set()
    for p in ("i-i", "i-ii", "ii-i", "ii-ii", "iii-i", "iii-ii", "iv-i", "iv-ii",
              "1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2"):
        if p in t or p.replace("-", " ") in t or p.replace("-", "") in t:
            sems.add(p.replace("-", ""))
    for yr in ("1st year", "2nd year", "3rd year", "4th year", "first year", "second year", "third year", "fourth year"):
        if yr in t:
            sems.add(yr.split()[0])
    for sem in ("sem 1", "sem 2", "sem 3", "sem 4", "sem 5", "sem 6", "sem 7", "sem 8",
                "semester 1", "semester 2", "semester 3", "semester 4"):
        if sem in t:
            sems.add(sem.replace("ester", "").replace(" ", ""))
    return sems


def _extract_branches(text: str) -> set[str]:
    """Extract department/branch names from text."""
    t = (text or "").lower()
    branches = set()
    if "cse" in t or "computer science" in t:
        branches.add("cse")
    if "ece" in t or "electronics" in t or "communication" in t:
        branches.add("ece")
    if "eee" in t or "electrical" in t:
        branches.add("eee")
    if "civil" in t:
        branches.add("civil")
    if "mech" in t or "mechanical" in t:
        branches.add("mech")
    if ("it" in t and "title" not in t) or "information technology" in t:
        branches.add("it")
    if "mba" in t or "management" in t:
        branches.add("mba")
    if "mca" in t or "computer applications" in t:
        branches.add("mca")
    if "pharm" in t or "pharmacy" in t:
        branches.add("pharmacy")
    return branches


_MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

# Same trigger words used for the timetable PAGE_CATALOGUE entry — kept in
# sync so "recency mode" only turns on for the query types it's meant for.
_TIMETABLE_QUERY_MARKERS = ("timetable", "time table", "exam schedule", "exam date",
                            "mid exam", "end exam", "mid-1", "mid-2", "i mid", "ii mid")


def _extract_recency(text: str) -> int:
    """
    Best-effort (year*12 + month) extracted from a title/URL string —
    used only to rank "which timetable is newest" among several matches
    on the same page. Returns 0 if no year is found (treated as oldest).
    """
    if not text:
        return 0
    t = text.lower()
    year = 0
    for m in re.finditer(r"(20[1-3][0-9])", t):
        y = int(m.group(1))
        if y > year:
            year = y
    if not year:
        return 0
    month = 0
    for name, num in _MONTH_NAMES.items():
        if name in t:
            month = max(month, num)
    return year * 12 + month


def _score_relevance(query: str, title: str, url: str, is_pdf: bool = False) -> float:
    """
    Score 0.0 - 1.0 for link or PDF relevance against the user's query.
    Takes into account regulation, branch/course, semester/year, document type, and token overlap.
    """
    try:
        combined = f"{title} {url}"
        norm_q = _normalize_text(query)
        norm_c = _normalize_text(combined)

        q_words = set(norm_q.split()) - _PDF_STOP
        c_words = set(norm_c.split())

        if not q_words:
            return 0.0

        # Base token match (0.0 to 0.4)
        overlap = len(q_words & c_words) / len(q_words)
        score = overlap * 0.4

        # Regulation match (e.g. R19, R20, R23)
        q_regs = _extract_regulations(query)
        c_regs = _extract_regulations(combined)
        if q_regs:
            if q_regs & c_regs:
                score += 0.35
            elif c_regs:
                score -= 0.15

        # Branch match (e.g. CSE, ECE, EEE, Civil, Mechanical, IT)
        q_branches = _extract_branches(query)
        c_branches = _extract_branches(combined)
        if q_branches:
            if q_branches & c_branches:
                score += 0.30
            elif c_branches:
                score -= 0.15

        # Semester / Year match (e.g. II-I, 2nd year, Sem 1)
        q_sems = _extract_semesters(query)
        c_sems = _extract_semesters(combined)
        if q_sems:
            if q_sems & c_sems:
                score += 0.25

        # Document type match
        for doc_type in ("syllabus", "syllabi", "timetable", "schedule", "regulation",
                         "calendar", "fee", "result", "notification", "curriculum"):
            if doc_type in norm_q and doc_type in norm_c:
                score += 0.20
                break

        if is_pdf and combined.lower().endswith(".pdf"):
            score += 0.10

        # ── Recency boost — TIMETABLE QUERIES ONLY ──
        # When the user is asking about timetables, prefer the newest dated
        # page/PDF over older archived ones. Gated strictly to timetable-type
        # queries so no other scoring behavior (fees, syllabus, results, etc.)
        # is affected.
        if any(marker in query.lower() for marker in _TIMETABLE_QUERY_MARKERS):
            recency = _extract_recency(combined)
            if recency:
                baseline_months = 2018 * 12  # arbitrary fixed reference point
                months_since = max(0, recency - baseline_months)
                recency_bonus = min(0.4, months_since * (0.4 / 144))  # ramps to cap over ~12 yrs
                score += recency_bonus

        return max(0.0, min(1.0, score))
    except Exception:
        return 0.0


def _link_score(query: str, title: str, url: str) -> float:
    """Score 0-1 for internal HTML links."""
    return _score_relevance(query, title, url, is_pdf=False)


def _pdf_score(query: str, title: str, url: str) -> float:
    """Score 0–1 for PDF links."""
    return _score_relevance(query, title, url, is_pdf=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page selection
# ─────────────────────────────────────────────────────────────────────────────

def _pick_pages(query: str) -> list[tuple[str, str]]:
    """Always returns at least one page (the homepage fallback)."""
    pages, _ = _pick_pages_with_confidence(query)
    return pages


def _pick_pages_with_confidence(query: str) -> tuple[list[tuple[str, str]], bool]:
    """
    Same as _pick_pages, but also returns has_specific_match:
    True if the query hit a specific PAGE_CATALOGUE keyword entry
    (e.g. "principal" -> the Principal Profile page), as opposed to
    only falling back to the two generic homepages.
    """
    q = (query or "").lower()
    matched = []
    try:
        for keywords, url, label in PAGE_CATALOGUE:
            if any(kw in q for kw in keywords):
                matched.append((url, label))
    except Exception:
        pass
    has_specific_match = len(matched) > 0

    old_home = ("https://jntugvcev.edu.in/", "JNTU-GV CEV (Old Official Website)")
    new_home = ("https://www.jntugv.edu.in/", "JNTU-GV University (New Official Website)")

    if not any(p[0] == old_home[0] for p in matched):
        matched.append(old_home)
    if not any(p[0] == new_home[0] for p in matched):
        matched.append(new_home)
    return matched, has_specific_match


# ─────────────────────────────────────────────────────────────────────────────
# Public API — GUARANTEED to always return valid objects
# ─────────────────────────────────────────────────────────────────────────────

def _is_list_query(query: str) -> bool:
    """Return True when the user is asking for a complete list."""
    q = query.lower()
    list_triggers = (
        "all departments", "departments available", "list of departments",
        "what departments", "which departments", "how many departments",
        "all courses", "courses available", "list of courses", "what courses",
        "all programs", "programs available", "list of programs",
        "all branches", "branches available", "what branches",
        "facilities available", "list of facilities",
        "laboratories", "all labs", "clubs available",
        "departments and courses", "courses and departments",
        "what is offered", "what do you offer",
    )
    return any(t in q for t in list_triggers)


def retrieve(query: str) -> RetrievalResult:
    """
    Fetch the best official JNTU-GV page for the query.
    ALWAYS returns a RetrievalResult dataclass — never None, never raises.
    Check result.found to know whether live data was available.
    """
    result = RetrievalResult()

    if not query or not query.strip():
        result.error = "Empty query"
        return result

    if not _HAS_REQUESTS:
        result.error = "requests library not installed"
        return result

    if not _HAS_BS4:
        result.error = "beautifulsoup4 not installed"
        return result

    try:
        pages, has_specific_match = _pick_pages_with_confidence(query)
        is_list  = _is_list_query(query)

        # Always fetch up to 3 pages to ensure we check both the specific match AND both official homepages
        max_pages = len(pages) if is_list else 3

        merged_text  = []
        merged_pdfs  = []
        all_internal = []
        seen_urls    = set()

        for page_url, label in pages[:max_pages]:
            try:
                print(f"[WebRetriever] Fetching: {page_url}")
                html = _get_text(page_url)

                if not html:
                    print(f"[WebRetriever] Empty response: {page_url}")
                    continue

                page_text, pdf_links, internal_links = _clean_html(html, page_url)

                # Collect PDF and internal links from all pages BEFORE checking page_text
                for pdf in pdf_links:
                    url = pdf.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        merged_pdfs.append(pdf)
                for lnk in internal_links:
                    url = lnk.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_internal.append(lnk)

                if not page_text.strip():
                    print(f"[WebRetriever] No text after cleaning: {page_url}")
                    continue

                # Set primary source on first successful page
                if not result.source_url:
                    result.source_url = page_url
                    result.title      = label
                    result.found      = True

                # Merge page text — prefix with source label so LLM knows origin
                merged_text.append(
                    f"--- {label} ({page_url}) ---\n{page_text}"
                )

            except Exception as page_err:
                print(f"[WebRetriever] Error processing {page_url}: {page_err}")
                continue

        # ── 1-Hop Dynamic Subpage Follower ──
        # Only run this when the catalog didn't already give us a confident,
        # specific page for the query. If it did (e.g. "principal" matched the
        # Principal Profile entry), trust it — don't let a homepage nav link
        # (whose text/order can vary run to run) silently override it.
        if all_internal and not has_specific_match:
            scored_links = sorted(
                all_internal,
                key=lambda l: _link_score(query, l.get("title", ""), l.get("url", "")),
                reverse=True
            )
            best_link = scored_links[0] if scored_links else None
            best_l_score = _link_score(query, best_link.get("title", ""), best_link.get("url", "")) if best_link else 0.0

            if best_link and best_l_score >= 0.15:
                follow_url = best_link.get("url", "")
                follow_title = best_link.get("title", follow_url)
                print(f"[WebRetriever] Following subpage link: {follow_url} (score {best_l_score:.2f})")
                try:
                    html_2 = _get_text(follow_url)
                    if html_2:
                        p_text_2, p_pdfs_2, _ = _clean_html(html_2, follow_url)
                        p_text_2 = p_text_2.strip() or "(Visual content or PDF links on subpage)"
                        merged_text.append(f"--- Subpage: {follow_title} ({follow_url}) ---\n{p_text_2}")
                        # Override primary source URL to point directly to the deeper subpage
                        result.source_url = follow_url
                        result.title = follow_title
                        result.found = True
                        for pdf in p_pdfs_2:
                            u = pdf.get("url", "")
                            if u and u not in seen_urls:
                                seen_urls.add(u)
                                merged_pdfs.append(pdf)
                except Exception as e:
                    print(f"[WebRetriever] Deep follow error: {e}")

        # Combine all page texts
        result.page_text = "\n\n".join(merged_text)

        # Pick and open the best PDF across all collected links and extract its content
        if merged_pdfs:
            try:
                scored = sorted(
                    merged_pdfs,
                    key=lambda p: _pdf_score(
                        query,
                        p.get("title", "") if isinstance(p, dict) else "",
                        p.get("url", "")   if isinstance(p, dict) else ""
                    ),
                    reverse=True,
                )
                best       = scored[0] if scored else None
                best_score = (
                    _pdf_score(
                        query,
                        best.get("title", "") if best else "",
                        best.get("url", "")   if best else ""
                    ) if best else 0.0
                )
                print(f"[WebRetriever] Best PDF: {best} (score={best_score:.2f})")

                # If a relevant PDF exists, open and extract its content
                if best and (best_score >= 0.05 or len(merged_pdfs) == 1):
                    pdf_url = best.get("url", "") if isinstance(best, dict) else ""
                    pdf_title = best.get("title", pdf_url) if isinstance(best, dict) else pdf_url
                    if pdf_url:
                        print(f"[WebRetriever] Opening & extracting PDF: {pdf_url}")
                        pdf_bytes = _get_bytes(pdf_url)
                        if pdf_bytes:
                            pdf_text = _extract_pdf(pdf_bytes)
                            if pdf_text.strip():
                                result.pdf_url   = pdf_url
                                result.pdf_title = pdf_title
                                result.pdf_text  = pdf_text
                                print(f"[WebRetriever] Extracted {len(pdf_text)} chars from PDF: {pdf_title}")
                                # Point primary source to the exact PDF URL so the reference link points directly to the document
                                result.source_url = pdf_url
                                result.title = pdf_title
            except Exception as pe:
                print(f"[WebRetriever] PDF processing error: {pe}")

    except Exception as outer_err:
        print(f"[WebRetriever] Outer error in retrieve(): {outer_err}")
        result.error = str(outer_err)

    return result


def build_context(result: RetrievalResult) -> str:
    """
    Build a context string from a RetrievalResult.
    ALWAYS returns a non-empty string — never None, never raises.
    """
    if result is None:
        return (
            "[OFFICIAL WEBSITE]\n"
            "Website content unavailable.\n"
            "Source: https://jntugvcev.edu.in/\n"
        )

    try:
        if not result.found:
            reason = result.error or "website unreachable"
            return (
                f"[OFFICIAL WEBSITE]\n"
                f"Live website content is currently unavailable ({reason}).\n"
                f"Source: https://jntugvcev.edu.in/\n"
            )

        parts = [
            f"[OFFICIAL WEBSITE — {result.title or 'JNTU-GV'}]\n"
            f"Source URL: {result.source_url}\n\n"
            f"{result.page_text or '(no text extracted)'}"
        ]

        if result.pdf_text and result.pdf_text.strip():
            parts.append(
                f"\n\n[OFFICIAL PDF — {result.pdf_title or 'document'}]\n"
                f"PDF URL: {result.pdf_url}\n\n"
                f"{result.pdf_text}"
            )
        elif result.pdf_url:
            parts.append(
                f"\n\n[OFFICIAL PDF LINK]\n"
                f"Title: {result.pdf_title or 'document'}\n"
                f"PDF URL: {result.pdf_url}\n"
                "(PDF is image-based — text extraction unavailable)"
            )

        return "\n".join(parts)

    except Exception as e:
        print(f"[WebRetriever] build_context error: {e}")
        return (
            "[OFFICIAL WEBSITE]\n"
            "Error building context.\n"
            "Source: https://jntugvcev.edu.in/\n"
        )