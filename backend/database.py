"""
数据库模型定义
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exam_data", "exam.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# 数据库引擎
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UploadStatus(enum.Enum):
    """上传状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Student(Base):
    """学生表"""
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    class_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    grades = relationship("Grade", back_populates="student")
    uploads = relationship("Upload", back_populates="student")


class Teacher(Base):
    """老师表"""
    __tablename__ = "teachers"
    
    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    exams = relationship("Exam", back_populates="teacher")


class Exam(Base):
    """考试表"""
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    subject = Column(String(50), nullable=False)
    class_name = Column(String(50), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    answer_key_file = Column(String(100), nullable=True)
    total_score = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    teacher = relationship("Teacher", back_populates="exams")
    grades = relationship("Grade", back_populates="exam")
    uploads = relationship("Upload", back_populates="exam")


class Grade(Base):
    """成绩表"""
    __tablename__ = "grades"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    score = Column(Float, nullable=False)
    report_file = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    student = relationship("Student", back_populates="grades")
    exam = relationship("Exam", back_populates="grades")


class Upload(Base):
    """上传记录表"""
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    image_file = Column(String(200), nullable=False)
    status = Column(String(20), default=UploadStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    student = relationship("Student", back_populates="uploads")
    exam = relationship("Exam", back_populates="uploads")


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)
