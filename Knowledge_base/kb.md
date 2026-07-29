# JNTU-GV Chatbot Knowledge Base

## 1. University Overview

Jawaharlal Nehru Technological University-Gurajada, Vizianagaram (JNTU-GV) is a university ecosystem with academic, admissions, audit, placement, library, hostel, and student support units [3]. The official university structure includes services such as grievances, online courses, library, hostels, placements, NSS, sports, incubation, and other student-facing units [3].

The chatbot should answer student queries about academics, admissions, exams, hostel life, and fees using simple, direct language. It should route users to the right office or page when the answer depends on program, year, or regulation.

## 2. Syllabus

The DAAP portal says it provides the latest approved course structures and detailed academic syllabi for all UG and PG programs, with official syllabus archives for R25, R24, R23, R20, R19, and R16 [5]. The syllabus page contains branch-wise and department-wise syllabus links for both PG and B.Tech programs [6].

### PG full-time syllabi

The PG syllabus list includes Electrical & Electronics Engineering, Mechanical Engineering, Electronics & Communication Engineering, Computer Science & Engineering, Information Technology, Metallurgical Engineering, and Masters in Business Administration [6].

### B.Tech full-time syllabi

The B.Tech syllabus list includes Civil Engineering, Electrical & Electronics Engineering, Mechanical Engineering, Electronics & Communication Engineering, Computer Science and Engineering, Information Technology, and Metallurgical Engineering [6].

### Syllabus FAQ

- Where can I find my syllabus? Use the official JNTU-GV syllabus page for your department and regulation [6].
- How do I know which regulation applies to me? Check the academic regulations page for the current rule set [2][5].
- Can I download the course structure too? Yes. The DAAP portal provides course and syllabus access for approved programs [5].

## 3. Admissions

Admission to regular B.Tech programmes is based on the rank secured in the Engineering, Agriculture and Medicine Common Entrance Test conducted by APSCHE, Andhra Pradesh [7]. Admission to regular M.Tech programmes is based on GATE or PGECET rank conducted by APSCHE, Andhra Pradesh [7]. The admissions section also includes opening and closing ranks for different branches and categories [7].

### Admissions FAQ

- How are B.Tech admissions done? Through AP EAMCET rank-based admission [7].
- How are M.Tech admissions done? Through GATE or PGECET rank-based admission [7].
- Can I check branch-wise rank trends? Yes. The admissions section publishes opening and closing ranks [7].

## 4. Timetables

The university publishes academic calendars and exam-related notices through official portals, and those should be treated as the source of truth for dates and schedules. Since timetables can change each semester, the chatbot should avoid hardcoding dates unless they come from an official notice.

## 5. Courses

The courses-offered page lists a broad range of UG programs, including B.Tech branches, B.Arch, B.Pharmacy, BBA, and BCA [3]. It also maps branches to AP EAPCET codes and JNTU-GV branch codes, which is useful for counselling, admissions, and branch selection queries [3].

### Core UG courses

| Program | Examples / Notes |
|---|---|
| B.Tech | Civil, EEE, Mechanical, ECE, CSE, IT, Chemical, EIE, Metallurgical, and many newer specializations [3] |
| B.Arch | Architecture [3] |
| B.Pharmacy | Pharmacy [3] |
| BBA | Bachelor of Business Administration [3] |
| BCA | Bachelor of Computer Application [3] |

## 6. Departments

The syllabus page shows department-wise syllabi for Civil, EEE, Mechanical, ECE, CSE, IT, Metallurgical Engineering, MCA, MBA, and other PG specializations [6]. The courses-offered page also gives a broad branch list that can be used for department routing [3].

For the chatbot, department answers should be linked to syllabus, course structure, admissions route, and relevant office or contact if available. This is especially useful when a user asks which department handles a course or where a branch-specific syllabus is located.

## 7. Campus Navigation

The official university structure includes central facilities such as the Central Library, student grievance, recruitment grievance, hostels, NSS, sports, incubation, and other student support units [3]. For navigation queries, the chatbot should answer in terms of destination and purpose, such as “go to the Central Library for books and study space” or “visit the Placement Cell for recruitment-related support.”

### Suggested navigation categories

- Academic blocks.
- Examination office.
- Admissions office.
- Central library.
- Placement cell.
- Hostels.
- Canteen and student services.
- Sports and NSS units.

## 8. Regulations

JNTU-GV maintains a dedicated academic regulations page listing UG and PG regulation versions [2][5]. For UG, the page includes R23 B.Tech Regulations, Regulations for Honors and Minors, R20, R19, R16, and R13 [2]. For PG, it lists M.Tech, MCA, and MBA regulation versions including R25 and earlier versions [2].

The chatbot should always tie rules to regulation year because attendance, grading, credits, and promotion criteria can differ by regulation [2][5]. For example, a student asking about R23 attendance rules should get an answer specific to R23, not a generic one.

## 9. Fee Structure

The fee structure page contains tuition and special fee details, plus the payment workflow [1]. The page includes year-wise fee details for multiple programs and payment options through SBI Collect and demand draft [1].

### Fee details

- B.Tech first-year tuition fee: 45,000 [1].
- B.Tech first-year admission fee: 5,000 [1].
- B.Tech special fee: 300 in the listed category [1].
- M.Tech first-year tuition fee: 50,000 [1].
- M.Tech first-year admission or development fee: 5,200 [1].
- MCA first-year tuition fee: 27,000 [1].
- MCA first-year admission or development fee: 5,200 [1].

### Payment process

The fee page gives an SBI Collect workflow: select Andhra Pradesh, choose Educational Institutions, select Principal JNTUK UCEV Vizianagaram, pick the fee category, enter details, pay via OTP, and then download and print the e-receipt [1]. It also states that payment can be made by DD in favor of Principal, JNTUK UCEV, payable at SBI, Lower Tank Bund, Vizianagaram branch [1].

### Fee FAQ

- How do I pay fees? Use the SBI Collect workflow or the DD method described on the fee structure page [1].
- What should I do after payment? Download and print the e-receipt [1].
- Where do I find fee details? On the official fee structure page [1].

## 10. Examinations

The university published a revised examination fee structure for regular and supplementary examinations for UG and PG [8]. The revision came into force from 01.06.2026 [9].

### Examination fee slabs

- 1 subject: 400 [9].
- 2 subjects: 700 [9].
- 3 subjects: 900 [9].
- 4 or more subjects: 1,000 [9].

The chatbot should answer examination queries using official notices and the user’s regulation or year whenever possible [8][9]. It should also distinguish between regular exams, supplementary exams, and any program-specific notices.

## 11. Placements

The JNTU-GV Placement Cell has its own official site, and the university structure also lists Training & Placement as a central unit [10][3]. This makes it a strong source for placement-related chatbot responses [10].

### Placement topics

- Placement cell purpose.
- Training programs.
- Recruiter visits.
- Eligibility for campus placements.
- Resume and interview support.
- Contact or portal for placement updates.

The chatbot should answer placement queries in a practical way, such as “The Placement Cell handles recruitment support and placement updates” [10].

## 12. Hostel Rules and Policies

The hostel manual exists as an official hostel document, and the university infrastructure includes hostel facilities [4][11]. The hostel fee and payment instructions also require proof of payment to be submitted at the hostel office [1].

### Hostel policy categories

- Admission and allotment rules.
- Mess and dining guidelines.
- Visiting hours.
- Room discipline and cleanliness.
- Prohibited items.
- Anti-ragging and campus conduct.
- Complaint escalation path.

### Hostel FAQ

- How do I apply for a hostel room? Apply through the hostel office or the hostel admission process announced by the university [4][11].
- What documents are usually required for hostel admission? Student ID, admission proof, fee receipt, and any hostel forms or certificates required by the hostel office [4].
- Where do I submit hostel payment proof? Print the e-receipt and submit it at the hostel office [1].
- How can I pay hostel-related fees? Use the SBI Collect workflow described on the fee page or the DD method if accepted [1].
- Can I pay hostel fees by demand draft? Yes, as described in the fee page [1].
- What should I do after paying hostel fees? Download, print, and submit the e-receipt [1].
- What if my hostel payment is not reflected? Keep the receipt and contact the hostel office with transaction details [1].
- Where can I find hostel rules? In the official hostel manual and hostel office notices [4].
- Is hostel allotment automatic after fee payment? No. Allotment depends on hostel rules, availability, and verification [4][11].

## 13. Recommended Bot Schema

| Field | Example |
|---|---|
| category | admissions |
| subcategory | B.Tech |
| question | How are B.Tech admissions done? |
| answer | Through AP EAMCET rank-based admission. |
| source | official admissions page |
| regulation | N/A |
| updated_at | 2026-07-27 |

Citations:
[1] Fee Structure | JNTU-GV https://jntugvcev.edu.in/academics/admissions/fee-structure/
[2] Academic Regulations | JNTU-GV https://jntugvcev.edu.in/academics/academic-regulations/
[3] Courses Offered - https://daa.jntugv.edu.in/coursesoffered/
[4] JNTUK JNTUK UCEV UCEV :: HOSTEL HOSTEL MANUAL MANUAL https://jntugvcev.edu.in/wp-content/uploads/2020/08/Hostels-2020-21.pdf
[5] DAAP Portal | JNTU-GV https://daap.jntugv.edu.in/regulations
[6] DAAP Portal | JNTU-GV https://daap.jntugv.edu.in/syllabus
[7] Admission Procedure | JNTU-GV https://jntugvcev.edu.in/academics/admissions/admission-procedure/
[8] Raaahn - api.jntugv.edu.in https://api.jntugv.edu.in/media/JNTUGV%20Revised%20Examination%20Fee%20Structure.pdf
[9] JNTUGV Revised Examination Fee Structure for Regular and ... https://www.jntufastupdates.com/jntugv-revised-examination-fee-structure/
[10] Placement Cell - JNTU-GV https://placementcell.jntugv.edu.in/
[11] JNTU-GV https://jntugv.edu.in/infrastructure/about-hostels
[12] JNTU-GV https://jntugv.edu.in/
[13] Public Self-Disclosure Portal https://dmc.jntugv.edu.in/governance/disclosures/ugc
[14] Jawaharlal Nehru Technological University Gurajada Vizianagaram ... https://collegedunia.com/university/63844-jawaharlal-nehru-technological-university-gurajada-vizianagaram/scholarship
[15] HOSTEL MANUAL (Approved by the Executive Council of ... https://www.jnu.ac.in/sites/default/files/naac-ssr/HostelManual.pdf
[16] Jawaharlal Nehru Technological University Hostel Fees ... https://www.kollegeapply.com/college/jawaharlal-nehru-technological-university-hyderabad-hostel
[17] JNTUK B.Tech Computer Science and Engineering: Fees 2026, Course ... https://collegedunia.com/college/57519-university-college-of-engineering-jntuk-vizianagaram/bachelor-of-technology-btech-computer-science-and-engineering-2049
[18] UGC Disclosure https://jntuh.ac.in/ugc-disclosure