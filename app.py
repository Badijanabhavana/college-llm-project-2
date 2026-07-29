from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import os
import re
from dotenv import load_dotenv
load_dotenv(override=True)
print(os.getenv("OPENROUTER_API_KEY"))
available_models = ["gpt-3.5-turbo"]
API_KEY = os.getenv("OPENROUTER_API_KEY","").strip()
print("KEY=",repr(API_KEY))

app = Flask(__name__)
app.secret_key = "super_peachy_secret_key"
import database
from flask import jsonify
from link_resolver import format_links_for_bot, resolve_links, fetch_document_content
from scrape_college import search_knowledge_file
from fetch_and_index import search_scraped
import web_retriever
from rag import rag_engine
import kb_loader

database.init_db()
kb_loader.init_kb(rag_engine)

otps = {}

# Detailed Mock Data for JNTU-GV
university_data = {
    "courses_overview": "<strong>📚 Academic Programs Overview</strong><br><br>"
                        "JNTU-GV offers a diverse portfolio of industry-aligned programs designed to foster innovation and leadership. "
                        "Our curriculum is constantly updated to meet global standards.<br><br>"
                        "<strong>Programs Offered:</strong><br>"
                        "• <strong>B.Tech</strong>: Computer Science (CSE), Electronics (ECE), Mechanical, Civil.<br>"
                        "• <strong>B.Sc</strong>: Physics, Chemistry, Mathematics.<br>"
                        "• <strong>Business</strong>: BBA, B.Com, MBA (Finance, Marketing, HR).<br>"
                        "• <strong>Computer Applications</strong>: MCA.<br>"
                        "• <strong>Postgraduate</strong>: M.Tech and PhD in various disciplines.<br><br>"
                        "<em>Tip: You can ask me specifically about any course, e.g., 'Tell me about CSE'.</em>",
                        
    "cse_details": "<strong>💻 Computer Science & Engineering (B.Tech - CSE)</strong><br><br>"
                   "The CSE program focuses on the core principles of computing, software development, and modern technologies. "
                   "It is designed to build a strong foundation in algorithms, system software, and emerging digital trends.<br><br>"
                   "<strong>Core Subjects:</strong> Data Structures, Artificial Intelligence, Machine Learning, Database Management, Cloud Computing, and Cyber Security.<br><br>"
                   "<strong>Career Scope:</strong> Graduates are highly sought after as Software Engineers, Data Scientists, Cloud Architects, and AI Specialists in top global tech firms.",

    "ece_details": "<strong>⚡ Electronics and Communication Engineering (B.Tech - ECE)</strong><br><br>"
                   "The ECE program bridges the gap between hardware and software, focusing on telecommunications, VLSI design, and embedded systems.<br><br>"
                   "<strong>Core Subjects:</strong> Digital Signal Processing, Microprocessors, VLSI Design, Integrated Circuits, and IoT Systems.<br><br>"
                   "<strong>Career Scope:</strong> Opportunities abound as Network Engineers, Embedded Developers, and Systems Engineers in telecommunications, aerospace, and consumer electronics.",
                   
    "mba_details": "<strong>📈 Master of Business Administration (MBA)</strong><br><br>"
                   "The JNTU-GV MBA program builds future leaders by emphasizing strategic thinking, management capabilities, and entrepreneurial spirit.<br><br>"
                   "<strong>Specializations:</strong> Finance, Human Resources, Marketing, and Operations.<br><br>"
                   "<strong>Career Scope:</strong> Graduates enter the corporate world as Investment Bankers, Marketing Managers, HR Directors, and Business Consultants.",

    "mca_details": "<strong>🖥️ Master of Computer Applications (MCA)</strong><br><br>"
                   "The JNTU-GV MCA program is a dynamic course covering advanced programming, application development, and enterprise software solutions.<br><br>"
                   "<strong>Core Subjects:</strong> Advanced Java, Python Programming, Software Engineering, Mobile App Development, and Web Technologies.<br><br>"
                   "<strong>Career Scope:</strong> Graduates flourish as App Developers, Systems Analysts, Tech Leads, and IT Consultants.",

    "fees": "<strong>💰 Fee Structure & Financial Aid</strong><br><br>"
            "As a government-affiliated university, our fees are strictly subsidized to ensure affordable education for all students without compromising on quality.<br><br>"
            "<strong>Annual Fee Breakdown:</strong><br>"
            "• <strong>B.Tech</strong>: ₹35,000 / year<br>"
            "• <strong>MBA</strong>: ₹25,000 / year<br>"
            "• <strong>MCA</strong>: ₹20,000 / year<br>"
            "• <strong>M.Tech</strong>: ₹30,000 / year<br>"
            "• <strong>Hostel & Mess</strong>: ₹25,000 / year<br><br>"
            "<strong>🎓 Financial Aid & Reimbursements:</strong><br>"
            "Eligible students can benefit from complete fee reimbursement through State Government schemes based on entrance exam merit and category guidelines.",
            
    "admission": "<strong>📝 Clear & Transparent Admission Process</strong><br><br>"
                 "Securing admission at JNTU-GV involves a highly transparent, merit-based process designed by the state government.<br><br>"
                 "<strong>Step-by-Step Guide:</strong><br>"
                 "1. <strong>Entrance Exams</strong>: You must qualify in state-level entrance examinations like TS/AP EAMCET, ICET, or GATE.<br>"
                 "2. <strong>Online Web Counseling</strong>: Participate strictly through the official state government counseling portals.<br>"
                 "3. <strong>Merit Allotment</strong>: Seat allocation is conducted entirely based on rank, category reservations, and established merit criteria.<br>"
                 "4. <strong>Document Verification</strong>: Present original documents at designated government helpline centers.<br>"
                 "5. <strong>Final Reporting</strong>: Submit your official allotment order and fee receipt at our university administration office to confirm enrollment.",
                 
    "facilities": "<strong>🏫 Premium Campus Facilities</strong><br><br>"
                  "Our expansive 150-acre campus provides an active and enriching environment, outfitted with modern infrastructure to support academic excellence.<br><br>"
                  "<strong>Key Features:</strong><br>"
                  "• <strong>Central Library</strong>: A vast, digitally enabled library with hundreds of thousands of academic books, international journals, and quiet reading zones.<br>"
                  "• <strong>Advanced Labs</strong>: Practical programming, hardware, and chemistry labs equipped with standard modern tools and internet connectivity.<br>"
                  "• <strong>Sports Complex</strong>: Wide open grounds dedicated to cricket, football, basketball, and an indoor athletics center.<br>"
                  "• <strong>Accommodations</strong>: Government-subsidized, highly secure, and hygienic hostels separate for boys and girls.<br>"
                  "• <strong>Transport & Food</strong>: A fully-functioning subsidized cafeteria and seamless connectivity via RTC buses.",
                  
    "placements": "<strong>💼 Placements & Career Growth</strong><br><br>"
                  "Our dedicated Career Development Center works tirelessly to ensure students are well-prepared for the professional world, yielding excellent placement records annually.<br><br>"
                  "<strong>Placement Highlights:</strong><br>"
                  "• <strong>Highest Package</strong>: ₹12 LPA (Lakhs Per Annum) offered by leading MNCs.<br>"
                  "• <strong>Average Package</strong>: ₹4.5 LPA across varying engineering and management disciplines.<br>"
                  "• <strong>Top Recruiters</strong>: Regular placement drives feature giants like TCS, Infosys, Wipro, Amazon, and multiple Public Sector Undertakings (PSUs).<br>"
                  "• <strong>Training Initiatives</strong>: We conduct rigorous aptitude, technical skill, and soft-skill workshops right from the third year.",

    "exams": "<strong>📅 Examination Patterns & Schedules</strong><br><br>"
             "Our assessment system is designed to ensure continuous learning and comprehensive evaluation throughout the semester.<br><br>"
             "<strong>Exam Details:</strong><br>"
             "• <strong>Mid-Term Examinations</strong>: Conducted twice per semester assessing half the syllabus each time to ensure steady progress.<br>"
             "• <strong>End-Term Examinations</strong>: A comprehensive final theory and practical exam evaluated by external and internal faculty.<br>"
             "• <strong>Grading System</strong>: We follow a widely accepted 10-point CGPA grading scale.<br>"
             "<em>The exact dates for upcoming exams are regularly updated on the student portal and campus notice boards.</em>",
             
    "hello": "<strong>👋 Welcome to JNTU-GV College Enquiry System. How can I assist you today?</strong><br><br>"
             "I am your dedicated AI Enquiry Assistant. I can provide detailed information about our curriculum, admission processes, fee structures, campus life, and placement records.<br><br>",
             
    "default": "<strong>🤖 I'm here to help!</strong><br><br>"
               "I didn't quite catch that. Could you please specify your question?<br><br>"
               "You can ask me detailed questions about:<br>"
               "• <strong>Courses</strong> (e.g., 'Tell me about CSE or MBA')<br>"
               "• <strong>Admissions</strong> (e.g., 'How to apply?')<br>"
               "• <strong>Fees</strong> (e.g., 'What is the fee structure?')<br>"
               "• <strong>Placements</strong> (e.g., 'Tell me about jobs')<br>"
               "• <strong>Exams & Facilities</strong>."
}

chat_sessions = {}

def format_bot_response(text):
    # 1. Convert markdown bold **text** to <strong>text</strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # 2. Convert markdown links: [Label](URL) -> <a href="URL" target="_blank" class="chat-link" rel="noopener noreferrer">Label</a>
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', r'<a href="\2" target="_blank" class="chat-link" rel="noopener noreferrer">\1</a>', text)
    
    # 3. Clean up plain URLs wrapped in brackets [http://...] or parentheses (http://...)
    # This prevents the brackets/parentheses from becoming part of the URL or button text.
    text = re.sub(r'\[(https?://[^\s\]]+)\]', r'\1', text)
    text = re.sub(r'\((https?://[^\s\)]+)\)', r'\1', text)
    
    # 3.5 Force Source links to display the actual URL instead of user-friendly text
    text = re.sub(r'(Source:(?:<[^>]+>|\s)*<a[^>]*href=["\']([^"\']+)["\'][^>]*>).*?(</a>)', r'\1\2\3', text, flags=re.IGNORECASE)

    
    # 4. Tokenize by HTML tags to locate raw URLs not inside anchor tags,
    # and convert them to clickable hyperlinks or buttons.
    parts = re.split(r'(<[^>]+>)', text)
    in_anchor = False
    
    for i in range(len(parts)):
        part = parts[i]
        if part.startswith('<'):
            tag_lower = part.lower()
            if tag_lower.startswith('<a ') or tag_lower == '<a>':
                in_anchor = True
            elif tag_lower == '</a>':
                in_anchor = False
        else:
            # We are in plain text segment
            if not in_anchor:
                # Find all URLs starting with http:// or https://
                url_pattern = r'\b(https?://[^\s<>"\']+)'
                
                def replace_url(match):
                    url = match.group(1)
                    
                    # Clean trailing punctuation from the URL (e.g. trailing dot, comma, paren)
                    trailing = ""
                    while url and url[-1] in ".,;!?)]}*":
                        trailing = url[-1] + trailing
                        url = url[:-1]
                        
                    # Check if the URL is under "For more information:"
                    before_match = part[:match.start()]
                    is_for_more_info = False
                    if "more information" in before_match.lower():
                        is_for_more_info = True
                    else:
                        # Check if "more information" was in the previous non-tag segments
                        for j in range(max(0, i-2), i):
                            if "more information" in parts[j].lower():
                                is_for_more_info = True
                                break
                                
                    if is_for_more_info:
                        return f'<a href="{url}" target="_blank" class="chat-btn" rel="noopener noreferrer">{url}</a>{trailing}'
                    else:
                        return f'<a href="{url}" target="_blank" class="chat-link" rel="noopener noreferrer">{url}</a>{trailing}'
                        
                parts[i] = re.sub(url_pattern, replace_url, part)
                
    text = "".join(parts)
    text = text.replace('\n', '<br>')
    return text

def get_bot_response(user_text, username):
    print("Request received")
    if not API_KEY or API_KEY == "your_api_key_here":
        return ("<strong>System Notice:</strong> LLM is offline — API Key missing. "
                "Set OPENROUTER_API_KEY in the <code>.env</code> file.")
    try:
        # ══════════════════════════════════════════════════════════════════
        # RETRIEVAL PIPELINE  (priority order)
        # 1. PRIMARY   — live official JNTU-GV website  (web_retriever)
        # 2. SECONDARY — FAISS RAG vector index         (rag_engine)
        # 3. FALLBACK  — scraped_data.json keyword search
        # ══════════════════════════════════════════════════════════════════

        # ── Detect list-type questions — need wider retrieval ────────────
        _list_triggers = (
            "all departments", "departments available", "list of departments",
            "what departments", "which departments", "how many departments",
            "course", "courses", "all courses", "courses available", "list of courses", "what courses",
            "all programs", "programs available", "list of programs",
            "all branches", "branches available", "what branches",
            "all facilities", "facilities available", "list of facilities",
            "all labs", "laboratories", "clubs available",
            "departments and courses", "courses and departments",
            "what is offered", "what do you offer", "what are the courses",
            "what are the departments", "available departments",
            "available courses", "available programs",
        )
        _q_lower  = user_text.lower()
        is_list_q = any(t in _q_lower for t in _list_triggers)
        rag_top_k     = 10 if is_list_q else 3
        scraped_top_k =  5 if is_list_q else 2
        print(f"[Pipeline] is_list_query={is_list_q}, rag_top_k={rag_top_k}")

        # ── 1. PRIMARY: live official website ────────────────────────────
        print("[Pipeline] Step 1: live web retrieval")
        try:
            web_result = web_retriever.retrieve(user_text)
            if web_result is None:
                web_result = web_retriever.RetrievalResult()
            web_context = web_retriever.build_context(web_result)
            if not web_context:
                web_context = "[OFFICIAL WEBSITE]\nWebsite content unavailable.\nSource: https://jntugvcev.edu.in/\n"
        except Exception as wr_err:
            print(f"[Pipeline] web_retriever error: {wr_err}")
            web_result  = web_retriever.RetrievalResult()
            web_context = "[OFFICIAL WEBSITE]\nWebsite content unavailable.\nSource: https://jntugvcev.edu.in/\n"

        # ── 2. SECONDARY: FAISS RAG ───────────────────────────────────────
        print("[Pipeline] Step 2: RAG retrieval")
        primary_rag_context = ""
        secondary_kb_context = ""
        try:
            # Retrieve chunks for primary RAG
            chunks = rag_engine.retrieve(user_text, top_k=rag_top_k)
            if chunks:
                primary_chunks = [c for c in chunks if c.get("source") != "kb_md"][:rag_top_k]
                
                if primary_chunks:
                    primary_rag_context = "\n\n[PRIMARY RAG]\n" + "\n".join(
                        f"[{c['title']}] {c['content'][:300]}" for c in primary_chunks
                    )
                print(f"[Pipeline] RAG returned {len(primary_chunks)} primary chunks")
        except Exception as e:
            print(f"[Pipeline] RAG error: {e}")

        # ── 3. FALLBACK: scraped_data.json ────────────────────────────────
        scraped_context = ""
        try:
            hits = search_scraped(user_text, top_k=scraped_top_k)
            if hits:
                scraped_context = "\n\n[PRIMARY SCRAPED]\n" + "\n".join(
                    f"{h['url']}: {h['snippet'][:200]}" for h in hits
                )
                print(f"[Pipeline] scraped_data gave {len(hits)} hits")
        except Exception as e:
            print(f"[Pipeline] scraped search error: {e}")

        # ── Combine context ───────────────────────────────────────────────
        full_context = web_context + primary_rag_context + scraped_context

        # ── Trim context to stay within token budget ─────────────────────
        # full_context can be very large — compress to keep total prompt within budget
        MAX_CTX = 2000
        if len(full_context) > MAX_CTX:
            query_words = set(re.findall(r'\b\w+\b', user_text.lower())) - {"what", "is", "the", "a", "an", "of", "in", "for", "to", "and", "or", "tell", "me", "about"}
            lines = full_context.split('\n')
            scored_lines = []
            for i, line in enumerate(lines):
                if not line.strip(): continue
                score = sum(1 for w in query_words if w in line.lower())
                if line.startswith('['): score += 10 # preserve source headers
                scored_lines.append((score, i, line))
            
            scored_lines.sort(key=lambda x: x[0], reverse=True)
            
            selected_indices = []
            current_len = 0
            for score, i, line in scored_lines:
                if current_len + len(line) > MAX_CTX:
                    break
                selected_indices.append(i)
                current_len += len(line) + 1
                
            selected_indices.sort()
            full_context = "\n".join([lines[i] for i in selected_indices])
            if len(full_context) > MAX_CTX:
                full_context = full_context[:MAX_CTX] + "\n...[context trimmed]"

        # ── System instruction (compact — every token counts) ─────────────
        completeness_note = (
            "\nCOMPLETENESS: List ALL departments/courses found in context. "
            "JNTU-GV has: B.Tech (CSE,IT,ECE,EEE,Mech,Civil), M.Tech, MBA, MCA, "
            "B.Pharmacy, M.Pharmacy, Ph.D. Never omit any.\n"
        ) if is_list_q else ""

        system_instruction = (
            "You are the official JNTU-GV College AI Assistant. Your task is to read the retrieved official webpage content and documents to provide direct, comprehensive, and structured answers to user questions.\n\n"
            
            "REQUIRED RESPONSE BEHAVIOR:\n"
            "1. READ WEBPAGE CONTENT & ANSWER DIRECTLY FIRST:\n"
            "   - Read the retrieved webpage text and document context thoroughly.\n"
            "   - Always provide a complete, direct answer FIRST using the retrieved official website information before providing any reference links.\n"
            "   - Do not merely provide website links or tell the user where to look.\n\n"

            "2. USE BULLET POINTS FOR STRUCTURED INFORMATION:\n"
            "   - Always use bullet points for structured information such as fees, courses, syllabus, departments, academic regulations, and administrative or admission procedures.\n"
            "   - Use clean, well-organized bullet points under bold headings.\n\n"

            "3. DO NOT REPLY WITH 'VISIT THE WEBSITE':\n"
            "   - NEVER reply with 'visit the website', 'check the official website', 'refer to the portal for details', or similar phrases when the information exists in the retrieved page.\n"
            "   - Always extract and present the actual factual details directly in your response.\n\n"

            "4. CHECK CONTEXT BEFORE SAYING INFORMATION IS UNAVAILABLE:\n"
            "   - Before replying 'I am sorry, that information is unavailable' or saying data is missing, check thoroughly whether the retrieved webpage content or attached documents contain relevant information, details, or related data that can be used to answer the question.\n"
            "   - If relevant information is present in the retrieved webpage/context, use it to answer the user's question directly.\n\n"

            "5. DOCUMENT SELECTION (COURSE, YEAR, SEMESTER, REGULATION):\n"
            "   - If a webpage contains multiple documents, PDFs, or links (such as multiple syllabus files, regulations, or examination timetables), identify and select the specific document or information that best matches the user's question parameters (such as course/branch like CSE/ECE, academic year, semester I/II, and regulation R19/R20/R23/R25).\n"
            "   - Provide the specific information and document reference relevant to the user's specified course, year, semester, or regulation.\n\n"

            "6. SOURCE LINK ONLY AT THE VERY END AS REFERENCE:\n"
            "   - Provide the source link ONLY after the complete direct answer at the very end of your response as a reference.\n"
            "   - Format strictly: Source: <a href=\"[Exact official page URL]\" target=\"_blank\">[User-friendly page name]</a>\n"
            "   - NEVER place source links before or inside the direct answer body.\n\n"

            "COURSE QUESTION FORMAT (Use for course/department queries):\n"
            "**UG Programs**\n"
            "• **B.Tech**\n"
            "  - CSE\n"
            "  - ECE\n"
            "  - EEE\n"
            "  - Civil\n"
            "  - Mechanical\n"
            "  - IT\n"
            "  - Metallurgical (if present)\n\n"
            "**PG Programs**\n"
            "• **M.Tech**\n"
            "• **MCA**\n"
            "• **MBA** (if present)\n\n"

            "STRICT CONSTRAINTS:\n"
            "1. Extract and provide factual details directly from the retrieved context. If information is present in both the 'New Official Website' and the 'Old Official Website', use the latest information from the New Official Website.\n"
            "2. Generate a natural answer with clean bullet points. NEVER copy Markdown brackets or raw context text chunks directly.\n"
            "3. NEVER display internal citation names like 'KB-5-Courses', 'Primary RAG', or any other internal source tags.\n"
            "4. Show only ONE unified response per query, not multiple versions.\n"
            "5. NEVER invent URLs or courses. Provide ONLY the single most relevant official page URL at the very end formatted strictly as an HTML anchor tag.\n"
            "6. NEVER return the homepage (https://jntugvcev.edu.in/) except when the user asks for the official website or about the university itself.\n"
            "7. No raw code in output (except the HTML anchor tag for the source).\n"
            "8. For fees: give exact ₹ amounts and detailed itemized breakdowns in bullet points.\n"
            "9. For timetables: list subjects, dates, and timings clearly in bullet points.\n"
            "10. MCA=4 semesters. B.Tech=8.\n"
            "11. When asked about the Principal, college, or administration, list the Principal, Vice Principal, Vice-Chancellor, and Registrar (if found in the context). Extract ONLY their names and qualifications.\n"
            + completeness_note +
            "\nCONTEXT:\n"
            f"{full_context}\n"
        )

        # ── Build message history ──────────
        # Send only the current user question and current context to avoid token limits
        messages = [{"role": "system", "content": system_instruction}]
        messages.append({"role": "user", "content": user_text})

        # ── Call OpenRouter ───────────────────────────────────────────────
        print("[Pipeline] Calling OpenRouter ...")
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": 256,
                "temperature": 0.3,
            },
            timeout=20,
        )
        print(f"[Pipeline] OpenRouter status: {resp.status_code}")
        data = resp.json()

        if "choices" not in data:
            return f"<strong>API Error:</strong> {data}"

        text = data["choices"][0]["message"]["content"]

        # Strip any raw HTML the LLM leaked
        text = re.sub(r'<(?!(?:br|strong|em|a|ul|li|b|i)[\s/>])[^>]+>', '', text)
        text = format_bot_response(text)

        # Log to database
        database.log_chat(username, user_text, text)

        # Flag vague responses
        vague = ["visit the official website", "refer to the official",
                 "check the notifications", "i don't have specific",
                 "i do not have specific", "not available in my"]
        if any(p in text.lower() for p in vague):
            database.add_unanswered(username, user_text)

        print("[Pipeline] Response sent")
        return text

    except requests.exceptions.Timeout:
        return "<strong>Error:</strong> The server took too long to respond. Please try again."
    except Exception as e:
        return f"<strong>Error:</strong> {str(e)}"


@app.before_request
def check_user_session():
    # These routes are always accessible — no session required
    public_endpoints = {
        'login', 'register', 'static', 'forgot_password',
        'reset_password', 'root', 'landing', 'contact', 'admin_login'
    }
    if not request.endpoint or request.endpoint in public_endpoints:
        return
    if "user" in session:
        if not database.get_user(session["user"]):
            session.pop("user", None)
            return redirect(url_for("login", msg="Session expired. Please register or login again."))

@app.route("/landing")
def landing():
    return render_template("landing.html")

@app.route("/contact", methods=["POST"])
def contact():
    name    = request.form.get("name", "").strip()
    email   = request.form.get("email", "").strip()
    subject = request.form.get("subject", "").strip()
    message = request.form.get("message", "").strip()
    if name and email and message:
        database.save_contact(name, email, subject, message)
        return redirect("/landing?contact=success#contact")
    return redirect("/landing?contact=error#contact")

@app.route("/")
def root():
    # Always show the landing page regardless of session state.
    # The user must explicitly click "Get Started" or "Login" to reach
    # the chatbot — a page refresh must never auto-redirect to /home.
    return render_template("landing.html")

@app.route("/home")
def home():
    if "user" not in session: return redirect(url_for("login"))
    is_admin = database.get_user_is_admin(session["user"])
    return render_template("index.html", current_user=session["user"], is_admin=is_admin)

@app.route("/about")
def about():
    if "user" not in session: return redirect(url_for("login"))
    content = "Welcome to the LLM-Based College Enquiry System developed for JNTU-GV.<br><br>This project is specifically designed to bridge the communication gap between prospective students and the university administration. Built with a robust Python Flask backend and a responsive, premium frontend UI, this system simulates an AI chatbot capable of guiding students regarding courses, fee structures, admissions, placements, and extensive campus facilities."
    return render_template("generic.html", current_user=session["user"], title="About the Project", content=content)

@app.route("/departments")
def departments():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("departments.html", current_user=session["user"])

@app.route("/admissions")
def admissions():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("admissions.html", current_user=session["user"])

@app.route("/fees")
def fees():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("generic.html", current_user=session["user"], title="Fees", content=university_data["fees"])

@app.route("/placements")
def placements():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("placements.html", current_user=session["user"])

@app.route("/campus")
def campus():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("campus.html", current_user=session["user"])

@app.route("/chat")
def chat():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("chat.html", current_user=session["user"])

@app.route("/admin/users")
def admin_users():
    if "user" not in session: return redirect(url_for("login"))
    if not database.get_user_is_admin(session["user"]): return redirect(url_for("home"))
    return render_template("admin_users.html", current_user=session["user"])

@app.route("/admin")
def admin_dashboard():
    if "user" not in session: return redirect(url_for("login"))
    if not database.get_user_is_admin(session["user"]):
        return redirect(url_for("home"))
    
    users_count = len(database.get_all_users())
    chat_history_full = database.get_chat_history()
    chat_history_count = len(chat_history_full)
    feedbacks_count = len(database.get_feedbacks())
    unanswered_count = len(database.get_unanswered())
    recent_activity = chat_history_full[:5]
    
    return render_template("admin_dashboard.html", current_user=session["user"],
                           users_count=users_count, chat_history_count=chat_history_count,
                           feedbacks_count=feedbacks_count, unanswered_count=unanswered_count,
                           recent_activity=recent_activity)

@app.route("/admin/chat_history")
def admin_chat_history():
    if "user" not in session: return redirect(url_for("login"))
    if not database.get_user_is_admin(session["user"]): return redirect(url_for("home"))
    return render_template("admin_chat_history.html", current_user=session["user"])

@app.route("/admin/feedback")
def admin_feedback():
    if "user" not in session: return redirect(url_for("login"))
    if not database.get_user_is_admin(session["user"]): return redirect(url_for("home"))
    return render_template("admin_feedback.html", current_user=session["user"])

@app.route("/admin/unanswered")
def admin_unanswered():
    if "user" not in session: return redirect(url_for("login"))
    if not database.get_user_is_admin(session["user"]): return redirect(url_for("home"))
    return render_template("admin_unanswered.html", current_user=session["user"])

@app.route("/rag_admin")
def rag_admin():
    if "user" not in session: return redirect(url_for("login"))
    if not database.get_user_is_admin(session["user"]):
        return redirect(url_for("home"))
    return render_template("rag_admin.html", current_user=session["user"])

@app.route("/unanswered")
def unanswered():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("unanswered.html", current_user=session["user"])

@app.route("/records")
def records():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("records.html", current_user=session["user"])

@app.route("/chat_history")
def chat_history():
    if "user" not in session: return redirect(url_for("login"))
    is_admin = database.get_user_is_admin(session["user"])
    return render_template("chat_history.html", current_user=session["user"], is_admin=is_admin)

@app.route("/api/users")
def api_users():
    if "user" not in session: return jsonify([]), 403
    if not database.get_user_is_admin(session["user"]): return jsonify([]), 403
    return jsonify(database.get_all_users())

@app.route("/api/delete_user", methods=["POST"])
def api_delete_user():
    if "user" not in session: return jsonify({"status": "error", "msg": "Unauthorized"}), 403
    if not database.get_user_is_admin(session["user"]): return jsonify({"status": "error", "msg": "Unauthorized"}), 403
    
    data = request.json
    target_user = data.get("username")
    
    if target_user == session["user"]:
        return jsonify({"status": "error", "msg": "Cannot delete your own account."}), 400
        
    database.delete_user(target_user)
    return jsonify({"status": "success"})

@app.route("/api/unanswered")
def api_unanswered():
    if "user" not in session: return jsonify([]), 403
    return jsonify(database.get_unanswered())

@app.route("/api/feedbacks")
def api_feedbacks():
    if "user" not in session: return jsonify([]), 403
    return jsonify(database.get_feedbacks())

# ── RAG Admin API ────────────────────────────────────────────────────────────

@app.route("/api/rag/documents")
def api_rag_documents():
    if "user" not in session: return jsonify([]), 403
    if not database.get_user_is_admin(session["user"]): return jsonify([]), 403
    return jsonify(rag_engine.get_all_documents())

@app.route("/api/rag/add", methods=["POST"])
def api_rag_add():
    if "user" not in session: return jsonify({"error": "Unauthorized"}), 403
    if not database.get_user_is_admin(session["user"]): return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not content:
        return jsonify({"error": "Title and content are required."}), 400
    doc = rag_engine.add_document(
        title=title,
        content=content,
        source="admin_ui",
        added_by=session["user"]
    )
    # Also persist to DB for record keeping
    database.add_rag_document(title, content, source="admin_ui", added_by=session["user"])
    return jsonify({"success": True, "doc": doc}), 201

@app.route("/api/rag/delete/<int:doc_index>", methods=["DELETE"])
def api_rag_delete(doc_index):
    if "user" not in session: return jsonify({"error": "Unauthorized"}), 403
    if not database.get_user_is_admin(session["user"]): return jsonify({"error": "Forbidden"}), 403
    try:
        rag_engine.delete_document(doc_index)
        return jsonify({"success": True})
    except IndexError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/my_chat_history")
def api_my_chat_history():
    if "user" not in session: return jsonify([]), 403
    username = session["user"]
    return jsonify(database.get_chat_history(username))

@app.route("/api/chat_history")
def api_chat_history():
    if "user" not in session: return jsonify([]), 403
    username = session["user"]
    if database.get_user_is_admin(username):
        return jsonify(database.get_chat_history())
    return jsonify(database.get_chat_history(username))

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if "user" not in session: return redirect(url_for("login"))
    if request.method == "POST":
        message = request.form.get("message")
        stars = int(request.form.get("stars", 5))
        database.add_feedback(session["user"], message, stars)
        return redirect(url_for("records"))
    return render_template("feedback.html", current_user=session["user"])

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    msg = request.args.get("msg")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = database.get_user(username)
        if user and user["password"] == password:
            session["user"] = username
            if database.get_user_is_admin(username):
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("home"))
        error = "Invalid credentials"
        return render_template("admin_login.html", error=error, msg=msg)
    return render_template("admin_login.html", msg=msg)

@app.route("/login", methods=["GET", "POST"])
def login():
    msg = request.args.get("msg")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = database.get_user(username)
        if user and user["password"] == password:
             session["user"] = username
             if database.get_user_is_admin(username):
                 return redirect(url_for("admin_dashboard"))
             return redirect(url_for("home"))
        error = "Invalid credentials"
        return render_template("login.html", error=error, msg=msg)
    return render_template("login.html", msg=msg)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        mobile = request.form.get("mobile")
        password = request.form.get("password")
        if database.get_user(username):
             error = "User already exists"
             return render_template("register.html", error=error)
        database.add_user(username, email, mobile, password)
        return redirect(url_for("login", msg="Registration successful. Please login."))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        identifier = request.form.get("identifier")
        found_username = None
        for user in database.get_all_users():
            if user["username"] == identifier or user["email"] == identifier or user["mobile"] == identifier:
                found_username = user["username"]
                break
        
        if found_username:
            # Generate a mock OTP (hardcoded to 1234 for testing purposes)
            otps[found_username] = "1234"
            # In a real application, send this OTP via SMS/Email
            return redirect(url_for("reset_password", username=found_username))
            
        error = "Account not found with that mobile number, email, or username."
        return render_template("forgot_password.html", error=error)
    return render_template("forgot_password.html")

@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    username = request.args.get("username") or request.form.get("username")
    if not username:
        return redirect(url_for("forgot_password"))
        
    if request.method == "POST":
        otp = request.form.get("otp")
        new_password = request.form.get("new_password")
        
        if username in otps and otps[username] == otp:
            database.update_password(username, new_password)
            del otps[username] # Clear OTP after success
            return redirect(url_for("login", msg="Password reset successfully! You can now login."))
        
        error = "Invalid OTP provided."
        return render_template("reset_password.html", error=error, username=username)
        
    return render_template("reset_password.html", username=username)



@app.route("/get", methods=["POST"])
def chatbot_response():
    try:
        user_msg = request.form["msg"]
        username = session.get("user", "guest")
        return get_bot_response(user_msg, username)
    except Exception as e:
        return str(e), 400

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)