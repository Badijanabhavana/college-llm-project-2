# -*- coding: utf-8 -*-
"""
rag.py — Retrieval-Augmented Generation Engine for JNTU-GV Enquiry System.

Uses:
  - sentence-transformers (all-MiniLM-L6-v2) for local CPU embeddings
  - FAISS for fast vector similarity search
  - Persists index + docs to disk so it survives restarts
"""

import os
import json
import numpy as np

INDEX_DIR = os.getenv("RAG_INDEX_DIR", "rag_index")
DOCS_FILE = os.path.join(INDEX_DIR, "documents.json")
INDEX_FILE = os.path.join(INDEX_DIR, "faiss.index")

# ── Seed knowledge base (mirrors the existing system_instruction text) ──────
SEED_DOCUMENTS = [
    {
        "title": "About JNTU-GV",
        "content": (
            "JNTU-GV: Jawaharlal Nehru Technological University Gurajada Vizianagaram. "
            "State government university in Vizianagaram, Andhra Pradesh — 535003. "
            "Constituent colleges: "
            "(1) JNTU-GV College of Engineering Vizianagaram (CEV) — main engineering college. "
            "(2) JNTU-GV College of Pharmaceutical Sciences Vizianagaram (CPSV). "
            "(3) JNTU-GV Tribal College of Engineering Kurupam (TECK). "
            "Campus area: 150 acres. Accreditation: NAAC, AICTE. "
            "Affiliated colleges: 200+ across north Andhra Pradesh. "
            "Vice-Chancellor: Prof. V. V. Subba Rao (Ph.D., IIT Kharagpur). "
            "Registrar (i/c): Prof. D. Rajya Lakshmi (M.Tech, Ph.D). "
            "Principal CEV (i/c): Prof. K. Chandra Bhushana Rao. "
            "Vice Principal: Prof. G. J. Nagaraju. "
            "Main website: https://www.jntugv.edu.in/ "
            "CEV website: https://jntugvcev.edu.in/ "
            "Contact: https://jntugvcev.edu.in/contact-us/telephone-directory/"
        ),
        "source": "seed",
    },
    {
        "title": "B.Tech Programs and Branches",
        "content": (
            "B.Tech duration: 4 years (8 semesters). "
            "Branches at JNTU-GV CEV: "
            "1. Computer Science and Engineering (CSE) — 120 seats. "
            "2. Electronics and Communication Engineering (ECE) — 60 seats. "
            "3. Electrical and Electronics Engineering (EEE) — 60 seats. "
            "4. Mechanical Engineering (MECH) — 60 seats. "
            "5. Civil Engineering (CIVIL) — 60 seats. "
            "6. Information Technology (IT) — 60 seats. "
            "PG Programs: MBA, MCA, M.Tech (CSE / VLSI / Structural / Power Electronics). "
            "Pharmacy: B.Pharmacy (CPSV), M.Pharmacy (CPSV). "
            "Research: Ph.D programs in all engineering and pharmacy streams. "
            "Eligibility B.Tech: 10+2 PCM with minimum 45% marks. "
            "Admission: AP EAPCET rank-based state web counseling. "
            "Annual fees B.Tech: Tuition ₹45,000 + Admission ₹5,000 + Special ₹300 = ~₹50,300/year. "
            "Fee reimbursement: Full tuition reimbursed for BC/SC/ST students (family income < ₹2.5L). "
            "Courses page: https://jntugvcev.edu.in/academics/courses-offered/"
        ),
        "source": "seed",
    },
    {
        "title": "CSE Department",
        "content": (
            "B.Tech CSE at JNTU-GV CEV. Duration: 4 years. "
            "Sem 1-2: Engineering Maths I & II, Engineering Physics, Engineering Chemistry, "
            "C Programming, Engineering Graphics, Environmental Science. "
            "Sem 3-4: Data Structures, Digital Logic Design, Computer Organisation, "
            "Java OOP, Database Management Systems, Discrete Mathematics. "
            "Sem 5-6: Operating Systems, Computer Networks, Compiler Design, "
            "Software Engineering, Web Technologies, Machine Learning, Artificial Intelligence. "
            "Sem 7-8: Cloud Computing, Cyber Security, Big Data Analytics, IoT, "
            "Project Work, Electives. "
            "Labs: C Programming, Data Structures, DBMS, Networks, ML Lab. "
            "Career: Software Engineer, Data Scientist, Cloud Architect, AI/ML Engineer. "
            "Top recruiters: TCS, Infosys, Wipro, Cognizant, Capgemini, Amazon, HCL. "
            "Department page: https://jntugvcev.edu.in/departments/cse/"
        ),
        "source": "seed",
    },
    {
        "title": "ECE Department",
        "content": (
            "B.Tech ECE at JNTU-GV CEV. Duration: 4 years. "
            "Core subjects: Electronic Devices and Circuits, Signals and Systems, "
            "Analog and Digital Communications, Electromagnetic Theory, "
            "Digital Signal Processing (DSP), Microprocessors and Microcontrollers, "
            "VLSI Design, Embedded Systems, Antenna and Wave Propagation, "
            "Mobile Communications, Optical Fibre Communications, IoT Systems. "
            "Labs: Basic Electronics, Communications, DSP, Microprocessor, VLSI Lab. "
            "Career: Network Engineer, Embedded Developer, VLSI Design Engineer, RF Engineer. "
            "Recruiters: Qualcomm, Intel, BSNL, DRDO, Tata Elxsi, HCL, TCS. "
            "Department page: https://jntugvcev.edu.in/departments/ece/"
        ),
        "source": "seed",
    },
    {
        "title": "EEE Department",
        "content": (
            "B.Tech EEE at JNTU-GV CEV. Duration: 4 years. "
            "Core subjects: Circuit Theory, Electrical Machines I & II, Power Systems I & II, "
            "Control Systems, Power Electronics, Switch Gear and Protection, "
            "High Voltage Engineering, Electrical Estimation, "
            "Power System Operation and Control. "
            "Labs: Electrical Machines, Power Electronics, Control Systems, Simulation Lab. "
            "Career: Electrical Engineer, Power Systems Engineer, Control Systems Engineer. "
            "Employers: APSPDCL, APTRANSCO, NTPC, BHEL, Siemens, ABB. "
            "Department page: https://jntugvcev.edu.in/departments/eee/"
        ),
        "source": "seed",
    },
    {
        "title": "Mechanical Engineering Department",
        "content": (
            "B.Tech Mechanical Engineering at JNTU-GV CEV. Duration: 4 years. "
            "Core subjects: Engineering Mechanics, Strength of Materials, Thermodynamics, "
            "Fluid Mechanics, Manufacturing Technology, Theory of Machines, "
            "Heat Transfer, Machine Design, Metrology, CAD/CAM, Industrial Engineering, Robotics. "
            "Labs: Workshop, Fluid Mechanics, Thermal Engineering, Metrology, CAD Lab. "
            "Career: Mechanical Engineer, Design Engineer, Production Engineer. "
            "Employers: BHEL, HAL, DRDO, Tata Motors, L&T, Ashok Leyland. "
            "Department page: https://jntugvcev.edu.in/departments/mechanical/"
        ),
        "source": "seed",
    },
    {
        "title": "Civil Engineering Department",
        "content": (
            "B.Tech Civil Engineering at JNTU-GV CEV. Duration: 4 years. "
            "Core subjects: Engineering Geology, Surveying, Fluid Mechanics, "
            "Structural Analysis I & II, Concrete Technology, Soil Mechanics, "
            "Transportation Engineering, Environmental Engineering, "
            "Foundation Engineering, Estimation and Costing, Remote Sensing and GIS. "
            "Labs: Survey Lab, Concrete Lab, Soil Mechanics Lab, Fluid Mechanics Lab. "
            "Career: Civil Engineer, Structural Engineer, Urban Planner. "
            "Employers: NHAI, APSRDC, L&T Construction, NCC Ltd, Government PWD. "
            "Department page: https://jntugvcev.edu.in/departments/civil/"
        ),
        "source": "seed",
    },
    {
        "title": "IT Department — Information Technology",
        "content": (
            "B.Tech Information Technology (IT) at JNTU-GV CEV. Duration: 4 years (8 semesters). "
            "Core subjects: Programming in C, Data Structures, Computer Networks, "
            "Database Management Systems, Operating Systems, Software Engineering, "
            "Web Technologies, Cloud Computing, Network Security, "
            "Internet of Things (IoT), Mobile Application Development, Big Data. "
            "Labs: Programming Lab, Networks Lab, DBMS Lab, Web Technologies Lab. "
            "Career: Software Developer, Network Administrator, Web Developer, "
            "Cloud Engineer, IT Consultant, System Analyst. "
            "Admission: AP EAPCET rank-based state web counseling. "
            "Department page: https://jntugvcev.edu.in/departments/it/"
        ),
        "source": "seed",
    },
    {
        "title": "B.Pharmacy Program",
        "content": (
            "B.Pharmacy at JNTU-GV College of Pharmaceutical Sciences Vizianagaram (CPSV). "
            "Duration: 4 years (8 semesters). "
            "Eligibility: 10+2 with Physics, Chemistry, Biology/Mathematics, min 45% marks. "
            "Admission: AP EAPCET (Pharmacy stream) rank-based state counseling. "
            "Core subjects: Pharmaceutics, Pharmacology, Medicinal Chemistry, "
            "Pharmacognosy, Pharmaceutical Analysis, Clinical Pharmacy, "
            "Hospital Pharmacy, Pharmaceutical Biotechnology, Pharmacokinetics. "
            "Labs: Pharmaceutical Chemistry Lab, Pharmacognosy Lab, "
            "Pharmacology Lab, Clinical Pharmacy Lab. "
            "Career: Pharmacist, Drug Inspector, Medical Representative, "
            "Research Scientist, Hospital Pharmacist, Quality Control Analyst. "
            "Annual fees: as per AP Government fee structure. "
            "Program page: https://jntugvcev.edu.in/academics/courses-offered/"
        ),
        "source": "seed",
    },
    {
        "title": "M.Pharmacy Program",
        "content": (
            "M.Pharmacy at JNTU-GV College of Pharmaceutical Sciences Vizianagaram (CPSV). "
            "Duration: 2 years (4 semesters). "
            "Eligibility: B.Pharmacy with min 55% marks. "
            "Admission: AP PGECET (Pharmacy) or GPAT score. "
            "Specializations: Pharmaceutics, Pharmaceutical Chemistry, "
            "Pharmacognosy, Pharmacology. "
            "Career: Researcher, Clinical Pharmacist, Drug Regulatory Affairs, Academic. "
            "Program page: https://jntugvcev.edu.in/academics/courses-offered/"
        ),
        "source": "seed",
    },
    {
        "title": "MBA Program",
        "content": (
            "MBA at JNTU-GV CEV. Duration: 2 years (4 semesters). "
            "Eligibility: Any bachelor's degree with min 50% marks. "
            "Admission: AP ICET rank-based state web counseling. "
            "Specializations: Finance, Human Resources, Marketing, Operations Management. "
            "Sem 1: Management and Organisational Behaviour, Business Communication, "
            "Managerial Economics, Financial Accounting and Analysis, Business Statistics. "
            "Sem 2: Marketing Management, HRM, Financial Management, "
            "Production and Operations Management, Business Research Methods. "
            "Sem 3-4: Specialisation electives + Summer Internship + Project. "
            "Annual fees: Tuition ₹27,000 + Admission ₹5,200 + Special ₹3,300 = ~₹35,500/year. "
            "Career: Business Analyst, HR Manager, Marketing Manager, Financial Analyst. "
            "Program page: https://jntugvcev.edu.in/academics/courses-offered/"
        ),
        "source": "seed",
    },
    {
        "title": "MCA Program",
        "content": (
            "MCA at JNTU-GV CEV. Duration: 2 years (4 semesters) — revised per UGC norms. "
            "Eligibility: Bachelor's degree with Mathematics, minimum 50% marks. "
            "Admission: AP ICET rank-based state web counseling. "
            "Sem 1: Mathematical Foundations of CS, Python Programming, "
            "Data Structures, DBMS, Web Technologies. "
            "Sem 2: Design and Analysis of Algorithms, Advanced Java, "
            "Operating Systems, Software Engineering, Mobile App Development. "
            "Sem 3-4: Cloud Computing, Machine Learning, Project Work, Electives. "
            "Annual fees: Tuition ₹27,000 + Admission ₹5,200 + Special ₹3,300 = ~₹35,500/year. "
            "Career: Software Developer, Systems Analyst, App Developer, Tech Lead, IT Consultant. "
            "Program page: https://jntugvcev.edu.in/academics/courses-offered/"
        ),
        "source": "seed",
    },
    {
        "title": "M.Tech Programs",
        "content": (
            "M.Tech at JNTU-GV CEV. Duration: 2 years (4 semesters). "
            "Eligibility: B.Tech/B.E. in relevant branch with min 50% marks. "
            "Admission: AP PGECET or GATE score-based counseling. "
            "Specializations: M.Tech CSE, VLSI and Embedded Systems, "
            "Structural Engineering, Power Electronics. "
            "Annual fees: Tuition ₹50,000 + Admission ₹5,200 + Special ₹3,300 = ~₹58,500/year. "
            "Structure: 2 semesters coursework + 2 semesters thesis/project. "
            "Program page: https://jntugvcev.edu.in/academics/courses-offered/"
        ),
        "source": "seed",
    },
    {
        "title": "Admissions",
        "content": (
            "Admission process for JNTU-GV CEV: "
            "B.Tech: AP EAPCET rank → AP web counseling → seat allotment → document verification → reporting. "
            "MBA/MCA: AP ICET rank → AP ICET counseling. "
            "M.Tech: GATE or AP PGECET score. "
            "Ph.D: JNTU-GV entrance test + interview. "
            "Documents required: EAPCET/ICET rank card, marks memos (all years), "
            "TC and Conduct Certificate, caste certificate (if applicable), "
            "income certificate (for fee reimbursement), Aadhaar card, photos, allotment order. "
            "Deadline: Report to college within 5 days of allotment with originals. "
            "Admissions page: https://jntugvcev.edu.in/academics/admissions/admission-procedure/ "
            "Fee structure: https://jntugvcev.edu.in/academics/admissions/fee-structure/"
        ),
        "source": "seed",
    },
    {
        "title": "Fee Structure",
        "content": (
            "Annual fee structure at JNTU-GV CEV: "
            "B.Tech: Tuition ₹45,000 + Admission ₹5,000 + Special ₹300 = ~₹50,300/year. "
            "MBA: Tuition ₹27,000 + Admission ₹5,200 + Special ₹3,300 = ~₹35,500/year. "
            "MCA: Tuition ₹27,000 + Admission ₹5,200 + Special ₹3,300 = ~₹35,500/year. "
            "M.Tech: Tuition ₹50,000 + Admission ₹5,200 + Special ₹3,300 = ~₹58,500/year. "
            "Hostel: ~₹25,000/year (includes mess). "
            "Fee reimbursement: Full tuition reimbursed by AP Govt for BC/SC/ST students "
            "with family income < ₹2.5 lakh/year. "
            "Payment: Challan at SBH/SBI or online via AP Government fee portal. "
            "Fee structure page: https://jntugvcev.edu.in/academics/admissions/fee-structure/"
        ),
        "source": "seed",
    },
    {
        "title": "Examinations and Timetable",
        "content": (
            "Examination system at JNTU-GV: semester-based with continuous evaluation. "
            "Mid-Term exams: 2 per semester. Mid-1 covers Units 1-3, Mid-2 covers Units 4-6. "
            "Each mid-term: 30 marks internal assessment. "
            "End-semester exam: 70 marks theory + practical exams separately. "
            "Grading: 10-point CGPA scale. Minimum passing CGPA: 5.0. "
            "Supplementary exams conducted for failed students each semester. "
            "Recent notifications (2026): "
            "- MCA & MBA II Sem Regular/Supply Exams: May 2026. "
            "- B.Tech Special Supplementary results: available on portal. "
            "- B.Pharmacy results: February 2026 declared. "
            "Postponement circulars posted on notifications page. "
            "Results: https://jntugvcev.edu.in/academics/examinations/results/ "
            "Timetables: https://jntugvcev.edu.in/academics/examinations/examination-time-tables/ "
            "Notifications: https://jntugvcev.edu.in/notifications/"
        ),
        "source": "seed",
    },
    {
        "title": "Online Portals",
        "content": (
            "JNTU-GV has two official websites: "
            "(1) University portal: https://jntugv.edu.in/ — exam results, notifications, regulations, examination branch. "
            "(2) College of Engineering Vizianagaram: https://jntugvcev.edu.in/ — academics, departments, admissions, facilities. "
            "DIRECT LINKS: "
            "Exam Results (university): https://jntugv.edu.in/results "
            "University Notifications: https://jntugv.edu.in/notifications "
            "Academic Regulations: https://jntugv.edu.in/regulations "
            "Examination Branch: https://jntugv.edu.in/examination "
            "University Academics: https://jntugv.edu.in/academics "
            "Exam timetables (CEV): https://jntugvcev.edu.in/academics/examinations/examination-time-tables/ "
            "CEV Notifications: https://jntugvcev.edu.in/notifications/ "
            "Admissions (CEV): https://jntugvcev.edu.in/academics/admissions/admission-procedure/ "
            "Fee structure (CEV): https://jntugvcev.edu.in/academics/admissions/fee-structure/ "
            "Courses offered (CEV): https://jntugvcev.edu.in/academics/courses-offered/ "
            "Placements (CEV): https://jntugvcev.edu.in/beta/placements/training-placements-cell/ "
            "Library: https://jntugvcev.edu.in/facilities/library/ "
            "Hostels: https://jntugvcev.edu.in/facilities/hostels/ "
            "R&D Cell: https://jntugvcev.edu.in/rd-cell/about-research/ "
            "Administration: https://jntugvcev.edu.in/admistration/ "
            "Contact: https://jntugvcev.edu.in/contact-us/telephone-directory/"
        ),
        "source": "seed",
    },
    {
        "title": "Placements",
        "content": (
            "The Placements Cell provides aptitude, technical, and soft skills training. "
            "Campus recruitment drives are held where top companies hire students. "
            "Companies like TCS, Infosys, Wipro participate regularly. "
            "Highest package: Rs 12 LPA. Average package: Rs 4.5 LPA. "
            "Career guidance starts from 3rd year. "
            "Placements page: https://jntugvcev.edu.in/beta/placements/training-placements-cell/"
        ),
        "source": "seed",
    },
    {
        "title": "Events and Activities",
        "content": (
            "Annual Day and Sports Day are held every year. "
            "NSS (National Service Scheme) is active with community programs. "
            "Student clubs: Music Club, Student Activity Club, Sports and Fitness. "
            "Major cultural event: Ityuktha 2K24. "
            "Inter-Collegiate Tournaments are organized every year. "
            "Republic Day, Women's Day, and Independence Day are celebrated on campus. "
            "Gallery/events page: https://jntugvcev.edu.in/gallery/"
        ),
        "source": "seed",
    },
    {
        "title": "Facilities and Hostels",
        "content": (
            "Separate hostels for boys and girls on campus. "
            "Sports facilities: volleyball, weightlifting, yoga courts. "
            "Central Library with hundreds of thousands of academic books and international journals. "
            "Advanced Labs: programming, hardware, chemistry labs with internet connectivity. "
            "Sports Complex: cricket, football, basketball, indoor athletics. "
            "Staff quarters available. Subsidized cafeteria, RTC bus connectivity. "
            "Facilities page: https://jntugvcev.edu.in/facilities/library/ "
            "Hostels page: https://jntugvcev.edu.in/facilities/hostels/"
        ),
        "source": "seed",
    },
    {
        "title": "Research",
        "content": (
            "The R&D Cell supports research scholars and faculty. "
            "Ph.D programs are offered across departments. "
            "Pre-Ph.D exams, subject lists, syllabus, and registration forms are available on the website. "
            "Springer journals are accessible for research. "
            "Research page: https://jntugvcev.edu.in/rd-cell/about-research/"
        ),
        "source": "seed",
    },
    {
        "title": "Cells and Committees",
        "content": (
            "IQAC: Internal Quality Assurance Cell. NSS Cell. "
            "Student Grievance Redressal. Ombudsman for student complaints. "
            "Recruitment Grievance Committee. University Coordinators for different functions. "
            "Incubation Center for startups. "
            "Cells page: https://jntugvcev.edu.in/student-corner/nss/"
        ),
        "source": "seed",
    },
    {
        "title": "Online Learning and SWAYAM",
        "content": (
            "Students can access Swayam Central for MOOC courses. "
            "UGC MOOCs are also available. "
            "Springer journals are accessible for research."
        ),
        "source": "seed",
    },
    {
        "title": "Social Media and Contact",
        "content": (
            "YouTube: https://www.youtube.com/@JNTUGV. "
            "Facebook: https://www.facebook.com/JNTUGurajada. "
            "Twitter/X: https://twitter.com/JNTU_Gurajada. "
            "Instagram: https://www.instagram.com/jntu_gurajada/. "
            "LinkedIn: https://www.linkedin.com/in/jntugurajada/. "
            "Contact page: https://jntugvcev.edu.in/contact-us/telephone-directory/"
        ),
        "source": "seed",
    },
]


class RAGEngine:
    """
    Retrieval-Augmented Generation engine.
    Manages a FAISS index of text chunk embeddings for semantic search.
    """

    def __init__(self):
        self._model = None   # lazy-loaded
        self._index = None   # FAISS index (lazy-loaded)
        self._documents: list[dict] = []  # parallel list to FAISS vectors
        self._loaded = False

    # -- Lazy initialisation -----------------------------------------------

    def _ensure_loaded(self):
        """Load (or create) the index and documents on first use."""
        if self._loaded:
            return
        self._load_model()
        os.makedirs(INDEX_DIR, exist_ok=True)
        if os.path.exists(DOCS_FILE) and os.path.exists(INDEX_FILE):
            self._load_from_disk()
        else:
            print("[RAG] No index found — building from seed knowledge base …")
            self._build_from_seed()
        self._loaded = True

    def _load_model(self):
        """Load the sentence-transformer model (downloads on first run)."""
        from sentence_transformers import SentenceTransformer
        print("[RAG] Loading embedding model (all-MiniLM-L6-v2) …")
        self._model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[RAG] Model loaded.")

    # -- Disk persistence ---------------------------------------------------

    def _load_from_disk(self):
        """Load existing FAISS index and documents from disk."""
        import faiss
        print(f"[RAG] Loading index from {INDEX_DIR} …")
        self._index = faiss.read_index(INDEX_FILE)
        with open(DOCS_FILE, "r", encoding="utf-8") as f:
            self._documents = json.load(f)
        print(f"[RAG] Loaded {len(self._documents)} documents.")

    def _save_to_disk(self):
        """Persist FAISS index and documents to disk."""
        import faiss
        os.makedirs(INDEX_DIR, exist_ok=True)
        faiss.write_index(self._index, INDEX_FILE)
        with open(DOCS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._documents, f, ensure_ascii=False, indent=2)

    # -- Seeding ------------------------------------------------------------

    def _build_from_seed(self):
        """Embed and index all SEED_DOCUMENTS, then save to disk."""
        texts = [d["content"] for d in SEED_DOCUMENTS]
        embeddings = self._embed(texts)
        self._init_index(embeddings)
        self._documents = list(SEED_DOCUMENTS)
        self._save_to_disk()
        print(f"[RAG] Index built with {len(self._documents)} seed documents.")

    # -- Core helpers -------------------------------------------------------

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalised embeddings as a float32 numpy array."""
        vecs = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        vecs = vecs.astype(np.float32)
        # Normalise so inner-product == cosine similarity
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / np.maximum(norms, 1e-10)
        return vecs

    def _init_index(self, embeddings: np.ndarray):
        """Create a new FAISS flat inner-product index."""
        import faiss
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)

    # -- Public API ---------------------------------------------------------

    def add_document(self, title: str, content: str, source: str = "admin", added_by: str = "admin"):
        """
        Add a single text chunk to the index.
        Returns the internal document dict.
        """
        self._ensure_loaded()
        doc = {"title": title, "content": content, "source": source, "added_by": added_by}
        embedding = self._embed([content])
        self._index.add(embedding)
        self._documents.append(doc)
        self._save_to_disk()
        return doc

    def retrieve(self, query: str, top_k: int = 4) -> list[dict]:
        """
        Retrieve the top_k most semantically relevant document chunks for `query`.
        Returns a list of dicts with keys: title, content, source, score.
        """
        self._ensure_loaded()
        if self._index.ntotal == 0:
            return []
        q_vec = self._embed([query])
        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(q_vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            doc = dict(self._documents[idx])
            doc["score"] = float(score)
            results.append(doc)
        return results

    def get_all_documents(self) -> list[dict]:
        """Return all documents currently in the index."""
        self._ensure_loaded()
        return list(self._documents)

    def rebuild_index(self, documents: list[dict]):
        """Rebuild the FAISS index from scratch with the given document list."""
        self._ensure_loaded()
        import faiss
        texts = [d["content"] for d in documents]
        embeddings = self._embed(texts)
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)
        self._documents = list(documents)
        self._save_to_disk()

    def delete_document(self, index: int):
        """
        Delete the document at position `index`.
        FAISS flat indices don't support deletion natively,
        so we rebuild the index from scratch minus the deleted doc.
        """
        self._ensure_loaded()
        if index < 0 or index >= len(self._documents):
            raise IndexError(f"Document index {index} out of range.")
        new_docs = [d for i, d in enumerate(self._documents) if i != index]
        self.rebuild_index(new_docs)

    @property
    def doc_count(self) -> int:
        self._ensure_loaded()
        return len(self._documents)


# Module-level singleton
rag_engine = RAGEngine()
