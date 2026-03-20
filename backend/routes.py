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

from database import get_db, init_db, Student, Teacher, Exam, Grade, Upload, AnswerKey

router = APIRouter()

# 数据目录 - 使用 /tmp 作为数据目录（生产环境可写）
DATA_DIR = os.environ.get("DATA_DIR", "/tmp/exam_data")
ANSWER_KEYS_DIR = os.path.join(DATA_DIR, "answer_keys")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
STUDENTS_DIR = os.path.join(DATA_DIR, "students")

# 确保目录存在
for dir_path in [ANSWER_KEYS_DIR, REPORTS_DIR, UPLOADS_DIR, STUDENTS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# 学科名称常量
SUBJECT_NAME = "计算机组成与体系结构"

# 考试类型选项
EXAM_TYPES = ["第一次考试", "第二次考试", "第三次考试", "期中考试", "期末考试"]

# 班级列表
CLASS_LIST = ["计算机2201班", "计算机2202班", "计算机2203班"]


# ============== Pydantic 模型 ==============

class LoginRequest(BaseModel):
    account: str
    role: str  # "student" or "teacher"


class LoginResponse(BaseModel):
    success: bool
    user_id: Optional[int] = None
    name: Optional[str] = None
    class_name: Optional[str] = None
    message: str


class GenerateReportRequest(BaseModel):
    exam_id: int


class UpdateAnswerKeyRequest(BaseModel):
    exam_id: int
    answer_key: dict


class ReGradeRequest(BaseModel):
    exam_id: int


class UploadResponse(BaseModel):
    success: bool
    upload_id: Optional[int] = None
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
                class_name=student.class_name,
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


# ============== 班级和考试列表接口 ==============

@router.get("/api/classes")
async def get_classes():
    """获取班级列表"""
    return {"classes": CLASS_LIST}


@router.get("/api/exam-types")
async def get_exam_types():
    """获取考试类型列表"""
    return {"exam_types": EXAM_TYPES}


@router.get("/api/exams")
async def get_exams(
    class_name: Optional[str] = None, 
    teacher_id: Optional[int] = None, 
    db: Session = Depends(get_db)
):
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
            "class_name": exam.class_name,
            "subject": SUBJECT_NAME,
            "total_score": exam.total_score
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
        status="pending"
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
        upload.status = "processing"
        db.commit()
        
        # 执行批改
        grading_service = GradingService()
        result = await grading_service.grade_exam(
            image_path=image_path,
            student_name=student.name,
            class_name=student.class_name,
            exam=exam,
            db=db
        )
        
        if result["success"]:
            # 删除旧成绩（如果存在）
            old_grade = db.query(Grade).filter(
                Grade.student_id == student.id,
                Grade.exam_id == exam.id
            ).first()
            if old_grade:
                db.delete(old_grade)
            
            # 保存成绩
            grade = Grade(
                student_id=student.id,
                exam_id=exam.id,
                score=result["score"],
                report_file=result["report_file"]
            )
            db.add(grade)
            
            # 更新上传状态
            upload.status = "completed"
            db.commit()
        else:
            upload.status = "failed"
            db.commit()
            
    except Exception as e:
        print(f"批改失败: {str(e)}")
        import traceback
        traceback.print_exc()
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if upload:
            upload.status = "failed"
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
            "subject": SUBJECT_NAME,
            "score": grade.score,
            "report_file": grade.report_file,
            "exam_date": grade.created_at.strftime("%Y-%m-%d") if grade.created_at else None
        })
    
    return result


# ============== 生成班级报告接口 ==============

@router.post("/api/generate-class-report")
async def generate_class_report(request: GenerateReportRequest, db: Session = Depends(get_db)):
    """生成班级报告"""
    exam_id = request.exam_id
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return {"success": False, "message": "考试不存在"}
    
    # 获取该考试所有学生成绩
    grades = db.query(Grade).filter(Grade.exam_id == exam_id).all()
    
    if not grades:
        return {"success": False, "message": "暂无学生成绩数据，请先上传试卷"}
    
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
            <div class="subtitle">{SUBJECT_NAME} · {exam.class_name}</div>
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


# ============== 标准答案管理接口 ==============

@router.get("/api/answer-key/{exam_id}")
async def get_answer_key(exam_id: int, db: Session = Depends(get_db)):
    """获取标准答案"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    # 从数据库获取标准答案
    answer_key = db.query(AnswerKey).filter(AnswerKey.exam_id == exam_id).first()
    
    if answer_key:
        return {
            "success": True,
            "exam_id": exam_id,
            "exam_name": exam.name,
            "class_name": exam.class_name,
            "answer_key": json.loads(answer_key.content),
            "updated_at": answer_key.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # 如果没有标准答案，返回默认模板
    default_answer_key = get_default_answer_key()
    return {
        "success": True,
        "exam_id": exam_id,
        "exam_name": exam.name,
        "class_name": exam.class_name,
        "answer_key": default_answer_key,
        "updated_at": None,
        "is_default": True
    }


def get_default_answer_key():
    """获取默认标准答案模板"""
    return {
        "subject": SUBJECT_NAME,
        "total_score": 100,
        "questions": [
            {
                "number": 1,
                "type": "选择题",
                "content": "计算机中，存储器的基本单位是？",
                "correct_answer": "B",
                "score": 10,
                "analysis": "存储器的基本单位是字节(Byte)。"
            },
            {
                "number": 2,
                "type": "选择题",
                "content": "CPU主要由哪两部分组成？",
                "correct_answer": "A",
                "score": 10,
                "analysis": "CPU主要由控制器和运算器组成。"
            },
            {
                "number": 3,
                "type": "填空题",
                "content": "1字节等于____位。",
                "correct_answer": "8",
                "score": 10,
                "analysis": "1字节(Byte) = 8位(bit)。"
            },
            {
                "number": 4,
                "type": "填空题",
                "content": "计算机的存储层次结构从快到慢依次为：寄存器、____、主存、辅存。",
                "correct_answer": "Cache或高速缓存",
                "score": 10,
                "analysis": "Cache(高速缓存)位于寄存器和主存之间。"
            },
            {
                "number": 5,
                "type": "简答题",
                "content": "简述冯·诺依曼计算机的基本原理。",
                "correct_answer": "存储程序原理：将程序和数据存储在存储器中，计算机自动地从存储器中取出指令执行。",
                "score": 20,
                "analysis": "冯·诺依曼结构的核心是存储程序原理。"
            },
            {
                "number": 6,
                "type": "计算题",
                "content": "将十进制数25转换为二进制。",
                "correct_answer": "11001",
                "score": 20,
                "analysis": "25 = 16 + 8 + 1 = 2^4 + 2^3 + 2^0 = 11001(二进制)"
            },
            {
                "number": 7,
                "type": "应用题",
                "content": "某计算机字长32位，地址线20根，求其最大可寻址空间。",
                "correct_answer": "1MB或2^20B",
                "score": 20,
                "analysis": "地址线20根，可寻址空间为2^20 = 1MB"
            }
        ]
    }


@router.post("/api/answer-key")
async def update_answer_key(request: UpdateAnswerKeyRequest, db: Session = Depends(get_db)):
    """更新标准答案"""
    exam = db.query(Exam).filter(Exam.id == request.exam_id).first()
    if not exam:
        return {"success": False, "message": "考试不存在"}
    
    # 验证答案格式
    if "questions" not in request.answer_key:
        return {"success": False, "message": "答案格式错误，缺少questions字段"}
    
    # 更新或创建标准答案
    answer_key = db.query(AnswerKey).filter(AnswerKey.exam_id == request.exam_id).first()
    
    if answer_key:
        answer_key.content = json.dumps(request.answer_key, ensure_ascii=False)
        answer_key.updated_at = datetime.now()
    else:
        answer_key = AnswerKey(
            exam_id=request.exam_id,
            content=json.dumps(request.answer_key, ensure_ascii=False)
        )
        db.add(answer_key)
    
    db.commit()
    
    # 同时保存到文件
    answer_key_path = os.path.join(ANSWER_KEYS_DIR, f"exam_{request.exam_id}.json")
    with open(answer_key_path, "w", encoding="utf-8") as f:
        json.dump(request.answer_key, f, ensure_ascii=False, indent=2)
    
    return {"success": True, "message": "标准答案更新成功"}


@router.post("/api/regrade")
async def regrade_exam(request: ReGradeRequest, db: Session = Depends(get_db)):
    """重新批改试卷"""
    exam = db.query(Exam).filter(Exam.id == request.exam_id).first()
    if not exam:
        return {"success": False, "message": "考试不存在"}
    
    # 检查是否有标准答案
    answer_key = db.query(AnswerKey).filter(AnswerKey.exam_id == request.exam_id).first()
    if not answer_key:
        return {"success": False, "message": "请先设置标准答案"}
    
    # 获取所有该考试的上传记录
    uploads = db.query(Upload).filter(Upload.exam_id == request.exam_id).all()
    
    if not uploads:
        return {"success": False, "message": "没有找到已上传的试卷"}
    
    # 异步重新批改所有试卷
    asyncio.create_task(regrade_all_uploads(uploads, exam, db))
    
    return {
        "success": True, 
        "message": f"正在重新批改 {len(uploads)} 份试卷，请稍后查看成绩"
    }


async def regrade_all_uploads(uploads: list, exam: Exam, db: Session):
    """重新批改所有上传的试卷"""
    from grading_service import GradingService
    
    grading_service = GradingService()
    
    for upload in uploads:
        try:
            student = db.query(Student).filter(Student.id == upload.student_id).first()
            if not student:
                continue
            
            image_path = os.path.join(UPLOADS_DIR, upload.image_file)
            if not os.path.exists(image_path):
                continue
            
            # 执行批改
            result = await grading_service.grade_exam(
                image_path=image_path,
                student_name=student.name,
                class_name=student.class_name,
                exam=exam,
                db=db
            )
            
            if result["success"]:
                # 更新成绩
                grade = db.query(Grade).filter(
                    Grade.student_id == student.id,
                    Grade.exam_id == exam.id
                ).first()
                
                if grade:
                    grade.score = result["score"]
                    grade.report_file = result["report_file"]
                else:
                    grade = Grade(
                        student_id=student.id,
                        exam_id=exam.id,
                        score=result["score"],
                        report_file=result["report_file"]
                    )
                    db.add(grade)
                
                upload.status = "completed"
                db.commit()
                
        except Exception as e:
            print(f"重新批改失败 (student_id={upload.student_id}): {str(e)}")
            upload.status = "failed"
            db.commit()


# ============== 查询上传状态接口 ==============

@router.get("/api/upload-status/{upload_id}")
async def get_upload_status(upload_id: int, db: Session = Depends(get_db)):
    """查询上传状态"""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    
    if not upload:
        return {"success": False, "message": "上传记录不存在"}
    
    status_messages = {
        "pending": "等待处理",
        "processing": "正在批改中...",
        "completed": "批改完成",
        "failed": "批改失败"
    }
    
    return {
        "success": True,
        "status": upload.status,
        "message": status_messages.get(upload.status, "未知状态")
    }


# ============== 初始化数据接口 ==============

@router.post("/api/init-data")
async def init_data(db: Session = Depends(get_db)):
    """初始化测试数据"""
    import random
    
    # 创建测试学生（每个班级若干学生）
    students_data = []
    for class_name in CLASS_LIST:
        for i in range(1, 6):
            student_num = f"{class_name[-4:]}{i:02d}"
            students_data.append({
                "account": f"student{student_num}",
                "name": f"学生{student_num}",
                "class_name": class_name
            })
    
    for data in students_data:
        existing = db.query(Student).filter(Student.account == data["account"]).first()
        if not existing:
            student = Student(**data)
            db.add(student)
    
    # 创建测试老师
    teachers_data = [
        {"account": "teacher001", "name": "张老师"},
        {"account": "teacher002", "name": "李老师"},
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
    
    # 为每个班级创建各种考试场次
    exams_data = []
    for class_name in CLASS_LIST:
        for exam_name in ["第一次考试", "期中考试", "第二次考试", "期末考试"]:
            exams_data.append({
                "name": exam_name,
                "class_name": class_name,
                "teacher_id": teacher1.id if teacher1 else 1,
                "total_score": 100
            })
    
    for data in exams_data:
        existing = db.query(Exam).filter(
            Exam.name == data["name"],
            Exam.class_name == data["class_name"]
        ).first()
        if not existing:
            exam = Exam(**data)
            db.add(exam)
    
    db.commit()
    
    # 获取第一个考试（用于生成示例报告）
    first_exam = db.query(Exam).filter(
        Exam.name == "第一次考试",
        Exam.class_name == CLASS_LIST[0]
    ).first()
    
    # 为第一个考试生成模拟成绩
    if first_exam:
        students = db.query(Student).filter(Student.class_name == CLASS_LIST[0]).all()
        
        for student in students:
            existing_grade = db.query(Grade).filter(
                Grade.student_id == student.id,
                Grade.exam_id == first_exam.id
            ).first()
            
            if not existing_grade:
                score = random.randint(60, 100)
                grade = Grade(
                    student_id=student.id,
                    exam_id=first_exam.id,
                    score=score,
                    report_file=f"student_{student.name}_exam_{first_exam.id}.html"
                )
                db.add(grade)
        
        db.commit()
    
    return {
        "success": True, 
        "message": f"测试数据初始化完成\n班级：{len(CLASS_LIST)}个\n学生：每个班级5人\n考试：每个班级4场考试"
    }
