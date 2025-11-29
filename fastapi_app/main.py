from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import asyncio

# Import all the necessary modules from your application structure
from . import crud, models, schema, security, payments, database
from .rag_service import RAGService
# Create the database tables if they don't exist
try:
    with database.engine.connect() as connection:
        connection.execute(text("ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS full_name VARCHAR"))
        connection.commit()
    models.Base.metadata.create_all(bind=database.engine)
    print("Database tables checked/created successfully.")
except Exception as e:
    print(f"Error creating database tables: {e}")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="CAT/GATE Mock Test Platform API",
    description="An AI-powered platform to generate mock exams with a secure payment and user system.",
    version="1.0.0"
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Initialize the RAG Services ---
# We'll create instances dynamically based on request

# --- Include Routers from other files ---
# Temporarily commented out to disable the payment system
# app.include_router(payments.router, prefix="/payments", tags=["Payments"])

# --- Authentication Endpoints ---

@app.post("/register", response_model=schema.User, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: schema.UserCreate, db: Session = Depends(database.get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/token", response_model=schema.Token, tags=["Authentication"])
def login_for_access_token(form_data: schema.OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": user.role.value,
            "name": user.full_name,
        }
    )
    return {"access_token": access_token, "token_type": "bearer", "user_name": user.full_name}

# --- Information Endpoints ---

@app.get("/gate-streams", tags=["Information"])
def get_gate_streams():
    """
    Returns a list of all 30 supported GATE streams.
    Useful for frontend dropdown menus and validation.
    """
    from .rag_service import GATE_STREAMS
    
    # Map stream codes to full names for better UX
    stream_info = {
        "AE": "Aerospace Engineering",
        "AG": "Agricultural Engineering", 
        "AR": "Architecture and Planning",
        "BM": "Biomedical Engineering",
        "BT": "Biotechnology",
        "CE": "Civil Engineering",
        "CH": "Chemical Engineering",
        "CS": "Computer Science and Information Technology",
        "CY": "Chemistry",
        "DA": "Data Science and Artificial Intelligence",
        "EC": "Electronics and Communication Engineering",
        "EE": "Electrical Engineering",
        "EN": "Environmental Science and Engineering",
        "ES": "Earth Sciences",
        "EY": "Ecology and Evolution",
        "GE": "Geology and Geophysics",
        "GG": "Geophysics",
        "IN": "Instrumentation Engineering",
        "MA": "Mathematics",
        "ME": "Mechanical Engineering",
        "MN": "Mining Engineering",
        "MT": "Metallurgical Engineering",
        "NM": "Naval Architecture and Marine Engineering",
        "PE": "Petroleum Engineering",
        "PH": "Physics",
        "PI": "Production and Industrial Engineering",
        "ST": "Statistics",
        "TF": "Textile Engineering and Fibre Science",
        "XE": "Engineering Sciences",
        "XL": "Life Sciences"
    }
    
    return {
        "total_streams": len(GATE_STREAMS),
        "streams": [{"code": code, "name": stream_info.get(code, "Unknown")} for code in GATE_STREAMS]
    }

# --- In-Memory Task Store (for demo purposes) ---
# In production, use Redis or a database
exam_tasks = {}

async def run_exam_generation(task_id: str, request: schema.ExamGenerationRequest, user_id: int, db_session):
    try:
        print(f"Task {task_id}: Starting generation for user {user_id}")
        rag_service = RAGService(request.exam_type)
        generated_exam = await rag_service.generate_full_exam(
            exam_name=request.exam_type,
            stream=request.stream,
            year=request.year
        )
        
        # Save the generated exam to database
        user = db_session.query(models.User).filter(models.User.id == user_id).first()
        if user:
            saved_exam = crud.create_generated_exam(
                db_session,
                user,
                request.exam_type,
                request.exam_name,
                request.stream,
                request.year,
                generated_exam
            )
            exam_tasks[task_id] = {"status": "completed", "result": generated_exam, "exam_id": saved_exam.id}
        else:
            exam_tasks[task_id] = {"status": "completed", "result": generated_exam}
        
        print(f"Task {task_id}: Completed successfully")
    except Exception as e:
        print(f"Task {task_id}: Failed with error: {e}")
        exam_tasks[task_id] = {"status": "failed", "error": str(e)}

# --- Core Application Endpoint ---

# --- MODIFIED: The endpoint now accepts a request body with parameters ---
@app.post("/generate-exam", tags=["Exam Generation"])
async def generate_new_exam(
    request: schema.ExamGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    Start generating a new mock exam in the background.
    Returns a task_id to poll for status.
    """
    task_id = str(uuid.uuid4())
    exam_tasks[task_id] = {"status": "processing"}
    
    background_tasks.add_task(run_exam_generation, task_id, request, current_user.id, db)
    
    return {"task_id": task_id, "status": "processing", "message": "Exam generation started"}

@app.get("/exam-status/{task_id}", tags=["Exam Generation"])
async def get_exam_status(task_id: str, current_user: models.User = Depends(security.get_current_user)):
    """
    Check the status of an exam generation task.
    """
    task = exam_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] == "completed":
        result = {
            "status": "completed",
            "result": task["result"]
        }
        # Include exam_id if available
        if "exam_id" in task:
            result["exam_id"] = task["exam_id"]
        return result
    elif task["status"] == "failed":
        return {"status": "failed", "error": task.get("error")}
    else:
        return {"status": "processing"}

# --- Exam Submission Endpoints ---

@app.post("/submit-exam", response_model=schema.ExamAttemptResponse, tags=["Exam Submission"])
def submit_exam(
    submission: schema.ExamSubmissionRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    attempt = crud.create_exam_attempt(db, current_user, submission)
    return attempt

@app.get("/generated-exams", response_model=list[schema.GeneratedExamResponse], tags=["Exam Generation"])
def get_generated_exams(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db),
    include_attempted: bool = False
):
    """Get all exams generated by the user (available exams)."""
    exams = crud.get_generated_exams(db, current_user, include_attempted=include_attempted)
    return exams

@app.get("/exam-history", response_model=list[schema.ExamAttemptResponse], tags=["Exam Submission"])
def get_exam_history(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db),
    limit: int = 20
):
    """Get all completed exam attempts with detailed statistics."""
    attempts = crud.get_exam_attempts(db, current_user, limit=limit)
    return attempts

# --- Admin-Only Endpoint for Demo ---

@app.get("/admin/dashboard", tags=["Admin"])
def get_admin_dashboard(current_admin: models.User = Depends(security.get_current_admin_user)):
    """
    An example of a protected endpoint that is only accessible to users with the 'admin' role.
    """
    return {"message": f"Welcome to the admin dashboard, {current_admin.email}!"}

