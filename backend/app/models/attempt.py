"""
attempt.py — Uses String(36) for ALL UUID columns.
Works for BOTH SQLite (stores as text) and PostgreSQL (auto-casts to uuid).
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, Index, JSON
from sqlalchemy.sql import func
from .base import BaseModel


class TestAttempt(BaseModel):
    __tablename__ = 'test_attempts'

    employee_id = Column(String(36), ForeignKey('employees.id'), nullable=False)
    topic_id = Column(String(36), ForeignKey('topics.id'), nullable=False)
    assignment_id = Column(String(36), ForeignKey('employee_topic_assignments.id'), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default='IN_PROGRESS')
    current_question_index = Column(Integer, default=0)
    score = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('employee_id', 'topic_id', 'attempt_number', name='uq_attempt_emp_topic_num'),
        CheckConstraint(attempt_number.in_([1, 2]), name='check_attempt_number'),
        CheckConstraint(status.in_(['IN_PROGRESS', 'COMPLETED']), name='check_attempt_status'),
        Index('ix_attempt_emp_topic_status', 'employee_id', 'topic_id', 'status'),
    )


class EmployeeTopicAssignment(BaseModel):
    __tablename__ = 'employee_topic_assignments'

    employee_id = Column(String(36), ForeignKey('employees.id'), nullable=False)
    topic_id = Column(String(36), ForeignKey('topics.id'), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    attempt1_id = Column(String(36), ForeignKey('test_attempts.id', use_alter=True), nullable=True)
    attempt2_id = Column(String(36), ForeignKey('test_attempts.id', use_alter=True), nullable=True)
    status = Column(String(30), default='ASSIGNED')
    seminar_confirmed = Column(Boolean, default=False)
    seminar_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('employee_id', 'topic_id', name='uq_assign_emp_topic'),
        Index('ix_assign_emp_topic', 'employee_id', 'topic_id'),
    )


class EmployeeTopicQuestion(BaseModel):
    __tablename__ = 'employee_topic_questions'

    assignment_id = Column(String(36), ForeignKey('employee_topic_assignments.id'), nullable=False)
    question_id = Column(String(36), ForeignKey('questions.id'), nullable=False)
    base_slot = Column(Integer, nullable=False)
    question_text_snapshot = Column(String, nullable=False)
    answers_snapshot = Column(JSON, nullable=False)
    correct_answer_id = Column(String(36), ForeignKey('question_answers.id'), nullable=False)

    __table_args__ = (
        UniqueConstraint('assignment_id', 'question_id', name='uq_assign_question'),
        UniqueConstraint('assignment_id', 'base_slot', name='uq_assign_slot'),
    )


class AttemptQuestion(BaseModel):
    __tablename__ = 'attempt_questions'

    attempt_id = Column(String(36), ForeignKey('test_attempts.id'), nullable=False)
    assignment_question_id = Column(String(36), ForeignKey('employee_topic_questions.id'), nullable=False)
    question_id = Column(String(36), ForeignKey('questions.id'), nullable=False)
    display_order = Column(Integer, nullable=False)
    answer_display_order = Column(JSON, nullable=False)
    question_started_at = Column(DateTime(timezone=True), nullable=True)
    question_deadline_at = Column(DateTime(timezone=True), nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    selected_answer_id = Column(String(36), ForeignKey('question_answers.id'), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    answer_status = Column(String(20), default='PENDING')

    __table_args__ = (
        UniqueConstraint('attempt_id', 'assignment_question_id', name='uq_attempt_assign_q'),
        UniqueConstraint('attempt_id', 'display_order', name='uq_attempt_order'),
        CheckConstraint(answer_status.in_(['PENDING', 'ANSWERED', 'TIMEOUT']), name='check_answer_status'),
        Index('ix_attempt_q_status', 'attempt_id', 'answer_status'),
    )
