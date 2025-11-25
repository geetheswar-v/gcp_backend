from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLAlchemyEnum, JSON
from sqlalchemy.orm import relationship
from .database import Base
import datetime
import enum

# Define an Enum for user roles to ensure data consistency
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

class User(Base):
    """
    SQLAlchemy model for the 'users' table.
    Now includes a 'role' to distinguish between regular users and admins.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    # Add the role column, with a default value of 'user'
    role = Column(SQLAlchemyEnum(UserRole), nullable=False, default=UserRole.USER)

    # This creates a one-to-one relationship with the Subscription model.
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    exam_attempts = relationship("ExamAttempt", back_populates="user", cascade="all, delete-orphan")

class Subscription(Base):
    """
    SQLAlchemy model for the 'subscriptions' table.
    This table will track the subscription status for each user.
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    payment_customer_id = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="subscription")

class ExamAttempt(Base):
    """
    Stores historical exam submissions for users.
    """
    __tablename__ = "exam_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exam_name = Column(String, nullable=False)
    stream = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    score = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    exam_data = Column(JSON, nullable=False)

    user = relationship("User", back_populates="exam_attempts")

