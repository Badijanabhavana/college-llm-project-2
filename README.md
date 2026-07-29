# LLM-Based College Enquiry System

A minimal, premium-designed, completely functional College Enquiry Web Application designed for **Jawaharlal Nehru Technological University Gurajada Vizianagaram (JNTU-GV)**. The application acts as a simulation of an AI chatbot responding to queries about the university, including programs offered, fee structures, application process, and campus facilities.

## 🚀 Features

- **Premium UI/UX:** Clean, modern, "ChatGPT-style" interface featuring soft peach gradient aesthetics, fully tailored responsive design, rounded components, and glass-morphism effects.
- **Instant Chat Support:** Interactively respond to student's questions regarding the university in real-time.
- **Rule-based NLP Engine:** Python backend actively matches user inputs with logic-driven keywords to present prompt and context-aware responses (no API costs).
- **Smooth Animations:** Includes typing indicators, responsive button scales, hovering shadows, and graceful message delivery animations.
- **No External Frameworks:** Built purely on Vanilla HTML & CSS without bulk from frontend frameworks for optimal performance.

## 🛠️ Tech Stack

- **Backend:** Python, Flask server
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, jQuery (for asynchronous chat requests)
- **Styling:** Custom Vanilla CSS Design System (`Outfit` Font Family)

## 📁 File Structure

```text
college llm project/
├── README.md               # Project documentation
├── app.py                  # Primary Flask backend and routing
└── templates/              # Contains the HTML structure
    └── index.html          # Frontend Application layout + embedded CSS/JS
```

## ⚙️ Prerequisites

To run this application locally, you need [Python](https://www.python.org/downloads/) installed on your system.

## 💻 Installation & Setup

1. **Navigate to the Project Directory**
   Ensure you are in the directory where `app.py` is located.
   ```bash
   cd "desktop\college llm project"
   ```

2. **Install Required Extensions (Flask)**
   If you don't already have Flask installed, install it using pip:
   ```bash
   pip install flask
   ```

3. **Run the Application**
   Run the backend execution script and initiate the server locally:
   ```bash
   python app.py
   ```

4. **Access the Website**
   Open any compatible web browser and launch the application by navigating to:
   ```text
   http://127.0.0.1:5000
   ```
   *or*
   ```text
   http://localhost:5000
   ```

## 💬 Chatbot Usage (Keywords)

The NLP system evaluates keywords to offer specific data contextually. Here are some terms you can test the Enquiry Bot with:

- **"courses", "program", "degree"** -> Responds with BTech, MBA, MCA offerings.
- **"fees", "cost"** -> Displays the per-course university fee structure.
- **"admission", "apply", "eligibility"** -> Shows steps for university admission processing.
- **"facilities", "hostel", "sports"** -> Describes the campus library, wifi availability, and labs.
- **"placements", "recruit", "package"** -> Lists highest packages and top industry recruiters.
- **"exam", "schedule"** -> Mid-term and end-term schedule.
- **"hello", "hi"** -> Welcoming gesture to start the conversation.

## 📝 License

This is designed as a mock Final Year MCA educational project. Free to manipulate, upgrade, or utilize anywhere.
