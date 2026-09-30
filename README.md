# LLM and RAG Based College Enquiry System

An AI-powered web-based college enquiry system developed for Jawaharlal Nehru Technological University Gurajada Vizianagaram (JNTU-GV). The system allows students, parents, faculty, and other visitors to ask college-related questions in natural language and receive relevant information through an LLM and Retrieval-Augmented Generation (RAG) approach.

The system retrieves relevant information from college website content and uses the retrieved information as context for GPT-3.5 Turbo to generate natural-language responses.

## Live Project

https://college-llm-production-a0fd.up.railway.app/

## Project Objective

The main objective of this project is to provide an intelligent and user-friendly platform for obtaining college-related information through natural-language queries.

It reduces the need for users to manually search through multiple college website pages and provides relevant information through an interactive enquiry interface.

## How the System Works

The system follows a Retrieval-Augmented Generation (RAG) pipeline:

Official College Website
        ↓
Web Scraping using BeautifulSoup
        ↓
Information Extraction and Text Chunking
        ↓
Sentence Transformers
        ↓
Vector Embeddings
        ↓
FAISS Vector Index
        ↓
User Question
        ↓
Relevant Information Retrieval
        ↓
Retrieved Context + User Question
        ↓
GPT-3.5 Turbo
        ↓
Generated Answer
        ↓
Response Displayed to User

### RAG Process

1. Relevant college information is obtained from the college website using web scraping.
2. The extracted information is processed and divided into smaller text chunks.
3. Sentence Transformers are used to generate vector embeddings for the text.
4. The embeddings are indexed using FAISS for efficient similarity-based retrieval.
5. When a user asks a question, the query is processed and relevant information is retrieved from the indexed content.
6. The retrieved information is provided as context to GPT-3.5 Turbo.
7. GPT-3.5 Turbo generates the final natural-language response.
8. The response is displayed through the web interface along with relevant source information where available.

## Key Features

- AI-powered college enquiry chatbot
- Retrieval-Augmented Generation (RAG)
- Natural-language question answering
- College information retrieval from website content
- Web scraping using BeautifulSoup
- Semantic retrieval using Sentence Transformers and FAISS
- GPT-3.5 Turbo based response generation
- User registration and login
- Student/user dashboard
- Chat history
- Feedback management
- Voice-based query input
- Admin dashboard
- User management
- Responsive web interface
- Source links for relevant information
- SQLite-based data management
- Web-based deployment using Railway

## Users

The system can be used by:

- Students
- Parents
- Faculty
- Visitors

Users can access the system through a web browser and ask college-related questions without manually searching through different website pages.

## Technology Stack

### Frontend
- HTML
- CSS
- JavaScript

### Backend
- Python
- Flask

### Database
- SQLite

### RAG and Information Retrieval
- BeautifulSoup
- Sentence Transformers
- FAISS

### Large Language Model
- GPT-3.5 Turbo

### Development Tools
- Visual Studio Code
- Git
- GitHub
- Google Chrome

### Deployment
- Railway

## Main Modules

### 1. User Registration and Login
Allows users to create accounts and securely access the application.

### 2. User Dashboard
Provides the user with access to the chatbot and other available functionalities.

### 3. AI College Enquiry Chatbot
Allows users to ask college-related questions using natural language and receive generated responses.

### 4. RAG Retrieval Module
Retrieves relevant college information from the indexed content before generating the response.

### 5. Voice Query Module
Allows users to provide queries through voice input.

### 6. Chat History
Maintains users' previous chatbot conversations for later reference.

### 7. Feedback Management
Allows users to provide feedback about the chatbot responses.

### 8. Admin Dashboard
Provides administrative functionality for monitoring the application and managing users and feedback.

## Project Structure

```text
college-llm-project/
│
├── app.py
├── database.py
├── database.db
│
├── rag.py
├── kb_loader.py
├── web_retriever.py
├── scrape_college.py
├── fetch_and_index.py
├── link_resolver.py
│
├── Knowledge_base/
│
├── templates/
│
├── static/
│
├── requirements.txt
├── render.yaml
└── README.md
```
### Important Files

- `app.py` – Main Flask application and application routes
- `database.py` – Handles SQLite database operations
- `database.db` – SQLite database
- `rag.py` – RAG retrieval and vector-search functionality
- `kb_loader.py` – Loads and processes knowledge-base content
- `web_retriever.py` – Handles retrieval of web content
- `scrape_college.py` – Handles college website scraping
- `fetch_and_index.py` – Fetches and indexes content
- `link_resolver.py` – Handles relevant source links
- `Knowledge_base/` – Contains knowledge-base content used by the application
- `templates/` – HTML templates for the web interface
- `static/` – CSS, JavaScript and other frontend resources
- `requirements.txt` – Python dependencies
## Database

SQLite is used to store application-related data such as:

- User information
- Login-related data
- Chat history
- Feedback
- Other application records

The database is used for application data, while the RAG pipeline is responsible for retrieving relevant college information.
## Local Installation

### 1. Clone the Repository

Clone the repository using:

    git clone https://github.com/Badijanabhavana/college-llm-project-2.git

### 2. Navigate to the Project Directory

    cd college-llm-project-2

### 3. Install Dependencies

    pip install -r requirements.txt

### 4. Configure the LLM API Key

Create a `.env` file and configure the required LLM API key according to the environment variable used by the application.

### 5. Run the Application

    python app.py

### 6. Open the Application

Open a web browser and visit:

    http://localhost:5000
## Project Workflow

User
↓
Registration / Login
↓
Chatbot Interface
↓
Natural-Language Query
↓
Flask Backend
↓
RAG Retrieval
↓
Relevant College Information
↓
GPT-3.5 Turbo
↓
Generated Response
↓
Response Displayed to User
## Advantages

- Provides quick access to college-related information
- Supports natural-language interaction
- Reduces manual searching through multiple web pages
- Uses retrieved information as context for LLM responses
- Provides an interactive and user-friendly interface
- Supports both text and voice-based queries
- Maintains chat history and feedback
- Can be accessed through a web browser

## Limitations

- The accuracy of responses depends on the available and indexed college information.
- Changes made to the college website may require updated retrieval and indexing.
- LLM-generated responses may occasionally require verification against the original source.
- The application depends on the availability of the deployed service and required external services.

## Project Information

**Project Title:** LLM and RAG Based College Enquiry System

**Project Type:** MCA Final-Year Academic Project

**Institution:** JNTUGV-CEV

**Deployment Platform:** Railway
