from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

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

# --- Core Application Endpoint ---

# --- MODIFIED: The endpoint now accepts a request body with parameters ---
@app.post("/generate-exam", tags=["Exam Generation"])
async def generate_new_exam(
    request: schema.ExamGenerationRequest,
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Generate a full, new mock exam based on the provided parameters.
    
    This is a protected endpoint. The user must provide a valid JWT access token.
    Supports both CAT and GATE exams with all 30 GATE streams.
    """
    try:
        print(f"Generating new {request.exam_name} exam for user: {current_user.email}")
        
        # Create appropriate RAG service instance based on exam type
        rag_service = RAGService(request.exam_name)
        
        # Pass the request parameters to the RAG service
        generated_exam = await rag_service.generate_full_exam(
            exam_name=request.exam_name,
            stream=request.stream,
            year=request.year
        )
        return generated_exam
    except Exception as e:
        print(f"An error occurred during exam generation: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred while generating the exam.")

# --- Exam Submission Endpoints ---

@app.post("/submit-exam", response_model=schema.ExamAttemptResponse, tags=["Exam Submission"])
def submit_exam(
    submission: schema.ExamSubmissionRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db)
):
    attempt = crud.create_exam_attempt(db, current_user, submission)
    return attempt

@app.get("/exam-history", response_model=list[schema.ExamAttemptResponse], tags=["Exam Submission"])
def get_exam_history(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(database.get_db),
    limit: int = 20
):
    attempts = crud.get_exam_attempts(db, current_user, limit=limit)
    return attempts

# --- Admin-Only Endpoint for Demo ---

@app.get("/admin/dashboard", tags=["Admin"])
def get_admin_dashboard(current_admin: models.User = Depends(security.get_current_admin_user)):
    """
    An example of a protected endpoint that is only accessible to users with the 'admin' role.
    """
    return {"message": f"Welcome to the admin dashboard, {current_admin.email}!"}

