from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Text, ForeignKey, JSON
from app.database.session import Base

class LMSUser(Base):
    """
    Read-only model representing a user in the massive LMS database.
    """
    __tablename__ = "users_user"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    email = Column(String, index=True)


class PracticeTest(Base):
    """
    Read-only model representing a student's practice test.
    """
    __tablename__ = "practice_practicetests"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)
    test_name = Column(String)
    score = Column(Integer)
    status = Column(Boolean)
    total_time_taken = Column(Integer)
    total_mcq = Column(Integer)


class AssessmentTest(Base):
    """
    Read-only model representing a student's mock/assessment test.
    """
    __tablename__ = "assessment_assessmenttests"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)
    score = Column(Integer)
    status = Column(Boolean)
    total_time_taken = Column(Integer)
    total_question = Column(Integer)


class CourseRestriction(Base):
    """
    Read-only model representing assigned courses to a user.
    """
    __tablename__ = "subscription_coursesubjectrestriction"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)
    course_id = Column(BigInteger)


class TestQuestion(Base):
    """
    Read-only model representing a question in the system.
    """
    __tablename__ = "questions_testquestions"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    question_type = Column(Integer)
    level = Column(Integer)
    simulation_type = Column(Integer)
    status = Column(Boolean)
    right_option_id = Column(BigInteger, nullable=True)  # Nullable for sim/essay questions


class QuestionOption(Base):
    """
    Read-only model representing the multiple choice options for a question.
    """
    __tablename__ = "questions_questionoptions"
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, index=True)
    test_question_id = Column(BigInteger, index=True)
    option = Column(Text)
