AI-Powered Mock Test Platform
This project is a complete backend system for a CAT/GATE mock test platform. It features an AI-powered question generation engine using a RAG (Retrieval-Augmented Generation) pipeline, a secure multi-user authentication system with role-based access, and support for all 30 GATE streams plus CAT exam sections. The platform uses advanced AI to generate contextually relevant practice questions.

Project Structure
The project is organized into three main directories to ensure a clear separation of concerns:

mock_test_project/
├── 📁 data_pipeline/      # Scripts for all offline data processing (PDFs -> Vector DB).
├── 📁 app_data/           # All processed data used by the live application.
├── 📁 fastapi_app/        # The live FastAPI web server.
├── 📄 .env                  # (To be created) Environment variables for configuration.
├── 📄 requirements.txt      # All Python dependencies.
└── 📄 README.md             # This file.

Setup and Installation
Follow these steps to set up the project environment and run the application.

Step 1: Prerequisites
Ensure you have the following installed on your system:

Python 3.10+

uv: The Python package installer and virtual environment manager.

PostgreSQL: The database used to store user and subscription data.

Step 2: Install Dependencies
Clone the repository to your local machine.

Navigate to the project's root directory (mock_test_project/).

Install all required Python packages using uv:

```uv sync```

Step 3: Set Up the PostgreSQL Database
The application requires a PostgreSQL database to store user accounts.

Connect to PostgreSQL as a superuser (e.g., postgres or your main user account):

```/Users/vaibhav.yadav/pgsql/bin/pg_ctl -D /Users/vaibhav.yadav/pgsql/data start```

Verify it's running 

```/Users/vaibhav.yadav/pgsql/bin/pg_isready```

Create a dedicated database for the application:

```CREATE DATABASE mock_test_db;```

Create a user for the application. It's good practice not to use the superuser for the application itself.

```CREATE USER my_app_user WITH PASSWORD 'your_secure_password';```

Grant all privileges on the new database to your new user:

```GRANT ALL PRIVILEGES ON DATABASE mock_test_db TO my_app_user;```

Exit psql by typing \q.

Step 4: Configure Environment Variables
Navigate into the 3_fastapi_app/ directory.

Create a file named .env.

Add the following configuration details to the .env file, replacing the placeholder values with your own:

# A long, random string for JWT security. Generate one with: openssl rand -hex 32
SECRET_KEY="your_super_long_random_secret_string_here"

# Your Gemini API key for AI question generation
GEMINI_API_KEY="your_gemini_api_key_here"
# Optional: override the default Gemini model (defaults to gemini-1.5-flash)
# GEMINI_MODEL="gemini-1.5-flash"

# Your PostgreSQL database credentials from Step 3
DB_USER="my_app_user"
DB_PASSWORD="your_secure_password"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="mock_test_db"

How to Use the Application
Phase 1: Run the Data Pipeline
This phase processes your raw PDFs into a searchable AI knowledge base. You only need to run this when you have new question papers to add.

Add PDFs: Place your question paper PDF files into the appropriate folders:
- CAT papers: `data_pipeline/source_pdfs/CAT/`  
- GATE papers: `data_pipeline/source_pdfs/GATE/`

Parse PDFs to JSON: From the project's root directory, run the parsing script (now supports both CAT and GATE):

```python -m data_pipeline.scripts.parse_pdfs```

Build Vector Database: Next, run the script to create the AI embeddings for both exam types:

```python -m data_pipeline.scripts.build_vector_db```

**Note**: The scripts automatically process both CAT and GATE exams. For GATE, ensure PDF filenames follow the pattern: `GATE-YYYY-STREAM-Session-N.pdf` (e.g., `GATE-2024-CS-Session-1.pdf`)

Phase 2: Initialize the Application Database
This is a one-time step to create the necessary tables and demo user accounts in your PostgreSQL database.

From the project's root directory, run the seed_db.py script:

```python -m fastapi_app.seed_db```

This will create the users and subscriptions tables and add two demo accounts: user@example.com and admin@example.com.

Phase 3: Start the Server
Make sure you are in the project's root directory.

Run the Uvicorn server with the following command:

```uvicorn 3_fastapi_app.main:app --reload```

The server should now be running on http://127.0.0.1:8000.

Phase 4: Test the API
Open your web browser and navigate to the interactive API documentation: http://127.0.0.1:8000/docs.

Register a new user or use the demo accounts at the /token endpoint to log in.

Sample registration payload:
```json
{
  "email": "student@example.com",
  "full_name": "Student Name",
  "password": "securePassword123"
}
```

User: user@example.com / password

Admin: admin@example.com / adminpassword

Copy the access_token you receive after logging in.

Click the "Authorize" button at the top right, paste your token in the format Bearer <your_token>, and authorize.

You can now use the protected /generate-exam endpoint to get your first AI-generated mock test!

### Submit Completed Exams
- `POST /submit-exam`: store a completed attempt for the logged-in user.
  ```json
  {
    "exam_name": "GATE",
    "stream": "CS",
    "year": 2025,
    "score": 58,
    "exam_data": {
      "responses": [...],
      "metadata": {...}
    }
  }
  ```
- `GET /exam-history`: retrieve the most recent submissions (optional `limit` query parameter, default 20).

## Supported Exam Types

### CAT (Common Admission Test)
- **Sections**: VARC (24 questions), DILR (22 questions), QA (22 questions)  
- **Question Types**: MCQ and TITA (Type In The Answer)
- **Sample Request**:
```json
{
    "exam_name": "CAT",
    "year": 2024
}
```

### GATE (Graduate Aptitude Test in Engineering) 
- **Streams**: All 30 streams supported (CS, EE, ME, CE, etc.)
- **Structure**: 65 questions per stream (10 GA + 55 Technical)
- **Question Types**: MCQ and NAT (Numerical Answer Type)
- **Sample Request**:
```json
{
    "exam_name": "GATE", 
    "stream": "CS",
    "year": 2024
}
```

### Available GATE Streams
Use the `/gate-streams` endpoint to get the complete list of 30 supported streams with their full names.

**Complete List**: AE, AG, AR, BM, BT, CE, CH, CS, CY, DA, EC, EE, EN, ES, EY, GE, GG, IN, MA, ME, MN, MT, NM, PE, PH, PI, ST, TF, XE, XL