from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import BaseModel

class Question(BaseModel):
    __tablename__ = 'questions'
    
    topic_id = Column(UUID(as_uuid=True), ForeignKey('topics.id'), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='ACTIVE')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        CheckConstraint(status.in_(['ACTIVE', 'ARCHIVED']), name='check_question_status'),
        Index('ix_question_topic_status', 'topic_id', 'status'),
    )

class QuestionAnswer(BaseModel):
    __tablename__ = 'question_answers'
    
    question_id = Column(UUID(as_uuid=True), ForeignKey('questions.id'), nullable=False)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    option_label = Column(String(5), nullable=False)
    sort_order = Column(Integer, nullable=False)
    
    __table_args__ = (
        CheckConstraint(option_label.in_(['А', 'Б', 'В', 'Г', 'A', 'B', 'C', 'D']), name='check_option_label'),
        CheckConstraint(sort_order.in_([1, 2, 3, 4]), name='check_sort_order'),
        Index('ix_question_answer_question_id', 'question_id', unique=False),
    )
