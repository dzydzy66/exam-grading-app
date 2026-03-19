"""
API 路由定义
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import shutil
import asyncio
from datetime import datetime

from database import get_db, init_db, Student, Teacher, Exam, Grade, Upload, UploadStatus

router = APIRouter()

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exam_data")
ANSWER_KEYS_DIR = os.path.join(DATA_DIR, "answer_keys")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
STUDENTS_DIR = os.path.join(DATA_DIR, "students")

# 确保目录存在
for dir_path in [ANSWER_KEYS_DIR, REPORTS_DIR, UPLOADS_DIR, STUDENTS_DIR]:
    os.makedirs(dir_path, exist_ok=True)


# ============== Pydantic 模型 ==============

class LoginRequest(BaseModel):
    account: str
    role: str  # "student" or "teacher"


class LoginResponse(BaseModel):
    success: bool
    user_id: Optional[int] = None
    name: Optional[str] = None
    message: str


class ExamInfo(BaseModel):
    id: int
    name: str
    subject: str
    class_name: str


class GradeInfo(BaseModel):
    id: int
    exam_name: str
    subject: str
    score: float
    report_file: Optional[str]
    exam_date: Optional[str]


class UploadResponse(BaseModel):
    success: bool
    upload_id: Optional[int] = None
    message: str


class ClassReportResponse(BaseModel):
    success: bool
    report_file: Optional[str] = None
    message: str


# ============== 登录接口 ==============

@router.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    if request.role == "student":
        student = db.query(Student).filter(Student.account == request.account).first()
        if student:
            return LoginResponse(
                success=True,
                user_id=student.id,
                name=student.name,
                message="登录成功"
            )
        else:
            return LoginResponse(
                success=False,
                message="学生账号不存在"
            )
    elif request.role == "teacher":
        teacher = db.query(Teacher).filter(Teacher.account == request.account).first()
        if teacher:
            return LoginResponse(
                success=True,
                user_id=teacher.id,
                name=teacher.name,
                message="登录成功"
            )
        else:
            return LoginResponse(
                success=False,
                message="老师账号不存在"
            )
    else:
        return LoginResponse(
            success=False,
            message="无效的角色类型"
        )


# ============== 考试列表接口 ==============

@router.get("/api/exams")
async def get_exams(class_name: Optional[str] = None, teacher_id: Optional[int] = None, db: Session = Depends(get_db)):
    """获取考试列表"""
    query = db.query(Exam)
    
    if class_name:
        query = query.filter(Exam.class_name == class_name)
    if teacher_id:
        query = query.filter(Exam.teacher_id == teacher_id)
    
    exams = query.all()
    return [
        {
            "id": exam.id,
            "name": exam.name,
            "subject": exam.subject,
            "class_name": exam.class_name
        }
        for exam in exams
    ]


# ============== 上传试卷接口 ==============

@router.post("/api/upload", response_model=UploadResponse)
async def upload_exam(
    student_id: int = Form(...),
    exam_id: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传试卷图片"""
    # 检查学生和考试是否存在
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return UploadResponse(success=False, message="学生不存在")
    
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return UploadResponse(success=False, message="考试不存在")
    
    # 保存图片文件
    file_ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
    file_name = f"student_{student_id}_exam_{exam_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
    file_path = os.path.join(UPLOADS_DIR, file_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    # 创建上传记录
    upload = Upload(
        student_id=student_id,
        exam_id=exam_id,
        image_file=file_name,
        status=UploadStatus.PENDING.value
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    # 异步处理批改任务
    asyncio.create_task(process_grading(upload.id, file_path, student, exam, db))
    
    return UploadResponse(
        success=True,
        upload_id=upload.id,
        message="试卷上传成功，正在批改中..."
    )


async def process_grading(upload_id: int, image_path: str, student: Student, exam: Exam, db: Session):
    """处理批改任务（异步）"""
    from grading_service import GradingService
    
    try:
        # 更新状态为处理中
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        upload.status = UploadStatus.PROCESSING.value
        db.commit()
        
        # 执行批改
        grading_service = GradingService()
        result = await grading_service.grade_exam(
            image_path=image_path,
            student_name=student.name,
            class_name=student.class_name,
            exam=exam
        )
        
        if result["success"]:
            # 保存成绩
            grade = Grade(
                student_id=student.id,
                exam_id=exam.id,
                score=result["score"],
                report_file=result["report_file"]
            )
            db.add(grade)
            
            # 更新上传状态
            upload.status = UploadStatus.COMPLETED.value
            db.commit()
        else:
            upload.status = UploadStatus.FAILED.value
            db.commit()
            
    except Exception as e:
        print(f"批改失败: {str(e)}")
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if upload:
            upload.status = UploadStatus.FAILED.value
            db.commit()


# ============== 查询学生成绩接口 ==============

@router.get("/api/grades")
async def get_grades(student_id: int, db: Session = Depends(get_db)):
    """查询学生成绩"""
    grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    
    result = []
    for grade in grades:
        exam = db.query(Exam).filter(Exam.id == grade.exam_id).first()
        result.append({
            "id": grade.id,
            "exam_name": exam.name if exam else "未知考试",
            "subject": exam.subject if exam else "未知科目",
            "score": grade.score,
            "report_file": grade.report_file,
            "exam_date": grade.created_at.strftime("%Y-%m-%d") if grade.created_at else None
        })
    
    return result


# ============== 生成班级报告接口 ==============

@router.post("/api/generate-class-report")
async def generate_class_report(exam_id: int, db: Session = Depends(get_db)):
    """生成班级报告"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return {"success": False, "message": "考试不存在"}
    
    # 获取该考试所有学生成绩
    grades = db.query(Grade).filter(Grade.exam_id == exam_id).all()
    
    if not grades:
        return {"success": False, "message": "暂无学生成绩数据"}
    
    # 计算统计数据
    scores = [g.score for g in grades]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    min_score = min(scores)
    
    # 生成报告文件
    report_file = f"class_exam_{exam_id}.html"
    report_path = os.path.join(REPORTS_DIR, report_file)
    
    # 构建学生成绩列表
    student_grades = []
    for grade in grades:
        student = db.query(Student).filter(Student.id == grade.student_id).first()
        if student:
            student_grades.append({
                "name": student.name,
                "score": grade.score,
                "report_file": grade.report_file
            })
    
    # 生成HTML报告
    html_content = generate_class_report_html(
        exam=exam,
        avg_score=avg_score,
        max_score=max_score,
        min_score=min_score,
        student_grades=student_grades
    )
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return {
        "success": True,
        "report_file": report_file,
        "message": "班级报告生成成功"
    }


def generate_class_report_html(exam, avg_score, max_score, min_score, student_grades):
    """生成班级报告HTML"""
    # 按成绩排序
    sorted_grades = sorted(student_grades, key=lambda x: x["score"], reverse=True)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{exam.name} - 班级成绩报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: #fff; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; text-align: center; }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header .subtitle {{ font-size: 16px; opacity: 0.9; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; background: #f8f9fa; }}
        .stat-card {{ background: white; padding: 25px; border-radius: 12px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
        .stat-value {{ font-size: 36px; font-weight: 700; color: #667eea; }}
        .stat-label {{ font-size: 14px; color: #666; margin-top: 8px; }}
        .content {{ padding: 30px; }}
        .section-title {{ font-size: 24px; font-weight: 700; color: #333; margin-bottom: 20px; padding-left: 15px; border-left: 4px solid #667eea; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #333; }}
        tr:hover {{ background: #f8f9fa; }}
        .rank {{ font-weight: 700; color: #667eea; }}
        .excellent {{ color: #10b981; font-weight: 600; }}
        .good {{ color: #3b82f6; font-weight: 600; }}
        .pass {{ color: #f59e0b; font-weight: 600; }}
        .fail {{ color: #ef4444; font-weight: 600; }}
        .footer {{ background: #333; color: white; text-align: center; padding: 20px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{exam.name}</h1>
            <div class="subtitle">{exam.subject} · {exam.class_name}</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{len(student_grades)}</div>
                <div class="stat-label">参考人数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{avg_score:.1f}</div>
                <div class="stat-label">平均分</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{max_score}</div>
                <div class="stat-label">最高分</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{min_score}</div>
                <div class="stat-label">最低分</div>
            </div>
        </div>
        
        <div class="content">
            <h2 class="section-title">学生成绩排名</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>学生姓名</th>
                        <th>得分</th>
                        <th>等级</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for idx, grade in enumerate(sorted_grades, 1):
        percentage = (grade["score"] / exam.total_score) * 100 if exam.total_score > 0 else 0
        if percentage >= 90:
            level_class = "excellent"
            level = "优秀"
        elif percentage >= 80:
            level_class = "good"
            level = "良好"
        elif percentage >= 60:
            level_class = "pass"
            level = "及格"
        else:
            level_class = "fail"
            level = "不及格"
        
        html += f"""                    <tr>
                        <td class="rank">{idx}</td>
                        <td>{grade["name"]}</td>
                        <td>{grade["score"]}</td>
                        <td class="{level_class}">{level}</td>
                    </tr>
"""
    
    html += """                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>本报告由试卷批改系统自动生成</p>
        </div>
    </div>
</body>
</html>"""
    
    return html


# ============== 查看报告接口 ==============

@router.get("/api/reports/{file_name}")
async def get_report(file_name: str):
    """获取报告HTML文件"""
    report_path = os.path.join(REPORTS_DIR, file_name)
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="报告文件不存在")
    
    return FileResponse(report_path, media_type="text/html")


# ============== 查询上传状态接口 ==============

@router.get("/api/upload-status/{upload_id}")
async def get_upload_status(upload_id: int, db: Session = Depends(get_db)):
    """查询上传状态"""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    
    if not upload:
        return {"success": False, "message": "上传记录不存在"}
    
    return {
        "success": True,
        "status": upload.status,
        "message": {
            "pending": "等待处理",
            "processing": "正在批改中...",
            "completed": "批改完成",
            "failed": "批改失败"
        }.get(upload.status, "未知状态")
    }


# ============== 初始化数据接口 ==============

@router.post("/api/init-data")
async def init_data(db: Session = Depends(get_db)):
    """初始化测试数据"""
    # 创建测试学生
    students_data = [
        {"account": "student001", "name": "张三", "class_name": "三年级一班"},
        {"account": "student002", "name": "李四", "class_name": "三年级一班"},
        {"account": "student003", "name": "王五", "class_name": "三年级一班"},
        {"account": "student004", "name": "赵六", "class_name": "三年级二班"},
        {"account": "student005", "name": "孙七", "class_name": "三年级二班"},
    ]
    
    for data in students_data:
        existing = db.query(Student).filter(Student.account == data["account"]).first()
        if not existing:
            student = Student(**data)
            db.add(student)
    
    # 创建测试老师
    teachers_data = [
        {"account": "teacher001", "name": "李老师"},
        {"account": "teacher002", "name": "王老师"},
    ]
    
    for data in teachers_data:
        existing = db.query(Teacher).filter(Teacher.account == data["account"]).first()
        if not existing:
            teacher = Teacher(**data)
            db.add(teacher)
    
    db.commit()
    
    # 获取老师ID
    teacher1 = db.query(Teacher).filter(Teacher.account == "teacher001").first()
    teacher2 = db.query(Teacher).filter(Teacher.account == "teacher002").first()
    
    # 创建测试考试
    exams_data = [
        {"name": "数学期中考试", "subject": "数学", "class_name": "三年级一班", "teacher_id": teacher1.id if teacher1 else 1, "total_score": 100},
        {"name": "语文期中考试", "subject": "语文", "class_name": "三年级一班", "teacher_id": teacher2.id if teacher2 else 2, "total_score": 100},
        {"name": "数学期中考试", "subject": "数学", "class_name": "三年级二班", "teacher_id": teacher1.id if teacher1 else 1, "total_score": 100},
    ]
    
    for data in exams_data:
        existing = db.query(Exam).filter(
            Exam.name == data["name"],
            Exam.class_name == data["class_name"]
        ).first()
        if not existing:
            exam = Exam(**data)
            db.add(exam)
    
    db.commit()
    
    # 创建标准答案文件
    answer_key = {
        "exam_id": "math_midterm_2024",
        "subject": "数学",
        "exam_name": "数学期中考试",
        "total_score": 100,
        "questions": [
            {
                "number": 1,
                "type": "选择题",
                "content": "下列哪个是质数？A. 4  B. 5  C. 6  D. 8",
                "correct_answer": "B",
                "score": 10,
                "analysis": "5只能被1和5整除，是质数。4、6、8都能被2整除，是合数。"
            },
            {
                "number": 2,
                "type": "选择题",
                "content": "15 + 27 = ?",
                "correct_answer": "42",
                "score": 10,
                "analysis": "15 + 27 = 42，计算正确。"
            },
            {
                "number": 3,
                "type": "填空题",
                "content": "100 - 36 = ____",
                "correct_answer": "64",
                "score": 15,
                "analysis": "100 - 36 = 64。"
            },
            {
                "number": 4,
                "type": "填空题",
                "content": "8 × 9 = ____",
                "correct_answer": "72",
                "score": 15,
                "analysis": "8 × 9 = 72。"
            },
            {
                "number": 5,
                "type": "计算题",
                "content": "计算：125 + 375 = ?",
                "correct_answer": "500",
                "score": 20,
                "analysis": "125 + 375 = 500。"
            },
            {
                "number": 6,
                "type": "计算题",
                "content": "计算：1000 - 456 = ?",
                "correct_answer": "544",
                "score": 20,
                "analysis": "1000 - 456 = 544。"
            },
            {
                "number": 7,
                "type": "应用题",
                "content": "小明有50元，买了3支铅笔，每支2元，还剩多少元？",
                "correct_answer": "44元",
                "score": 10,
                "analysis": "50 - 3 × 2 = 50 - 6 = 44元。"
            }
        ],
        "created_date": "2024-01-15",
        "last_modified": "2024-01-15",
        "created_by": "李老师"
    }
    
    answer_key_path = os.path.join(ANSWER_KEYS_DIR, "exam_1.json")
    with open(answer_key_path, "w", encoding="utf-8") as f:
        json.dump(answer_key, f, ensure_ascii=False, indent=2)
    
    return {"success": True, "message": "测试数据初始化完成"}
