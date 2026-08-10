"""
eco-chat.uz — Local SQLite Database Setup
JSONB → JSON (SQLite uchun)
"""
import asyncio
import os
import sys

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./ecochat_local.db"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, BigInteger, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func
import uuid as uuid_mod


class Base(DeclarativeBase):
    pass


def uuid_col(primary_key=False, fk=None, nullable=True):
    """UUID as String for SQLite compatibility."""
    if fk:
        return Column(String(36), ForeignKey(fk, use_alter=True), primary_key=primary_key, nullable=nullable, default=lambda: str(uuid_mod.uuid4()))
    return Column(String(36), primary_key=primary_key, nullable=nullable, default=lambda: str(uuid_mod.uuid4()))


class Admin(Base):
    __tablename__ = "admins"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Branch(Base):
    __tablename__ = "branches"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    name = Column(String(200), unique=True, nullable=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Employee(Base):
    __tablename__ = "employees"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String(300), nullable=False)
    phone = Column(String(20), nullable=True)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=True)
    registration_state = Column(String(30), default="PENDING")
    registered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Topic(Base):
    __tablename__ = "topics"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    short_name = Column(String(100), nullable=False)
    full_name = Column(String(500), nullable=False)
    sequence_order = Column(Integer, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    topic_id = Column(String(36), ForeignKey("topics.id"), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)


class QuestionAnswer(Base):
    __tablename__ = "question_answers"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    option_label = Column(String(1), nullable=False)
    sort_order = Column(Integer, nullable=False)


class EmployeeTopicAssignment(Base):
    __tablename__ = "employee_topic_assignments"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False)
    topic_id = Column(String(36), ForeignKey("topics.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    attempt1_id = Column(String(36), nullable=True)
    attempt2_id = Column(String(36), nullable=True)
    status = Column(String(30), default="ASSIGNED")
    seminar_confirmed = Column(Boolean, default=False)
    seminar_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("employee_id", "topic_id"),)


class EmployeeTopicQuestion(Base):
    __tablename__ = "employee_topic_questions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    assignment_id = Column(String(36), ForeignKey("employee_topic_assignments.id"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False)
    base_slot = Column(Integer, nullable=False)
    question_text_snapshot = Column(Text, nullable=False)
    answers_snapshot = Column(Text, nullable=False)   # JSON string (SQLite)
    correct_answer_id = Column(String(36), ForeignKey("question_answers.id"), nullable=False)
    __table_args__ = (
        UniqueConstraint("assignment_id", "question_id"),
        UniqueConstraint("assignment_id", "base_slot"),
    )


class TestAttempt(Base):
    __tablename__ = "test_attempts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    employee_id = Column(String(36), ForeignKey("employees.id"), nullable=False)
    topic_id = Column(String(36), ForeignKey("topics.id"), nullable=False)
    assignment_id = Column(String(36), ForeignKey("employee_topic_assignments.id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(20), default="IN_PROGRESS")
    current_question_index = Column(Integer, default=1)
    score = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("employee_id", "topic_id", "attempt_number"),)


class AttemptQuestion(Base):
    __tablename__ = "attempt_questions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    attempt_id = Column(String(36), ForeignKey("test_attempts.id"), nullable=False)
    assignment_question_id = Column(String(36), ForeignKey("employee_topic_questions.id"), nullable=False)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False)
    display_order = Column(Integer, nullable=False)
    answer_display_order = Column(Text, nullable=False)   # JSON string
    question_started_at = Column(DateTime(timezone=True), nullable=True)
    question_deadline_at = Column(DateTime(timezone=True), nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    selected_answer_id = Column(String(36), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    answer_status = Column(String(20), default="PENDING")
    __table_args__ = (
        UniqueConstraint("attempt_id", "assignment_question_id"),
        UniqueConstraint("attempt_id", "display_order"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    admin_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(36), nullable=True)
    old_value = Column(Text, nullable=True)   # JSON string
    new_value = Column(Text, nullable=True)   # JSON string
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


async def setup():
    print("SQLite DB yaratilmoqda...")
    engine = create_async_engine(
        "sqlite+aiosqlite:///./ecochat_local.db",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Barcha jadvallar tayyor!")


if __name__ == "__main__":
    asyncio.run(setup())
