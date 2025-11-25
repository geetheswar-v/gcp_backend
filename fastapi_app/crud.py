from sqlalchemy.orm import Session
from . import models, schema, security
import datetime
from typing import List

# --- User CRUD Functions ---

def get_user_by_email(db: Session, email: str):
    """
    Retrieves a single user from the database based on their email address.
    """
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schema.UserCreate, role: models.UserRole = models.UserRole.USER):
    """
    Creates a new user in the database with a specified role.
    
    Args:
        db (Session): The database session.
        user (schemas.UserCreate): The Pydantic schema containing user creation data.
        role (models.UserRole): The role to assign to the new user.
        
    Returns:
        models.User: The newly created user object.
    """
    hashed_password = security.get_password_hash(user.password)
    
    # Create a new SQLAlchemy User model instance, now including the role
    db_user = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Exam Attempt CRUD Functions ---

def create_exam_attempt(db: Session, user: models.User, submission: schema.ExamSubmissionRequest) -> models.ExamAttempt:
    attempt = models.ExamAttempt(
        user_id=user.id,
        exam_name=submission.exam_name,
        stream=submission.stream,
        year=submission.year,
        score=submission.score,
        exam_data=submission.exam_data,
        submitted_at=datetime.datetime.utcnow()
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt

def get_exam_attempts(db: Session, user: models.User, limit: int = 20) -> List[models.ExamAttempt]:
    return (
        db.query(models.ExamAttempt)
        .filter(models.ExamAttempt.user_id == user.id)
        .order_by(models.ExamAttempt.submitted_at.desc())
        .limit(limit)
        .all()
    )

# --- Subscription CRUD Functions ---

def get_subscription_by_user_id(db: Session, user_id: int):
    """
    Retrieves a user's subscription from the database.
    """
    return db.query(models.Subscription).filter(models.Subscription.user_id == user_id).first()

def create_or_update_subscription(db: Session, user_id: int, payment_customer_id: str, is_active: bool, expires_at: datetime):
    """
    Creates a new subscription for a user or updates their existing one.
    """
    db_subscription = get_subscription_by_user_id(db, user_id=user_id)
    
    if db_subscription:
        db_subscription.is_active = is_active
        db_subscription.expires_at = expires_at
        db_subscription.payment_customer_id = payment_customer_id
    else:
        db_subscription = models.Subscription(
            user_id=user_id,
            payment_customer_id=payment_customer_id,
            is_active=is_active,
            expires_at=expires_at
        )
        db.add(db_subscription)
        
    db.commit()
    db.refresh(db_subscription)
    return db_subscription

