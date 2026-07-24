from sqlalchemy import Column, Integer, String, JSON, Boolean
from app.database.base import Base

class Students(Base):
    """
    Read-only model representing student data created by another project.
    We use extend_existing=True in case the table is defined elsewhere.
    """
    __tablename__ = "students"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String)
    course_id = Column(String)
    enrollment_status = Column(String)
    performance_data = Column(JSON) # Can store flexible grading info
