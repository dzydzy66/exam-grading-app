"""
试卷批改系统 - FastAPI 主程序
"""
import os
import sys

# 数据目录 - 使用 /tmp 作为数据目录（生产环境可写）
DATA_DIR = "/tmp/exam_data"
os.makedirs(DATA_DIR, exist_ok=True)

# 设置数据库路径环境变量（必须在导入 database 之前）
os.environ["DB_PATH"] = os.path.join(DATA_DIR, "exam.db")

# 添加后端目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, SessionLocal, Student, Teacher, Exam
from routes import router

# 静态文件目录
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

# 确保目录存在
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)


def init_sample_data():
    """初始化示例数据"""
    try:
        db = SessionLocal()
        # 检查是否已有数据
        if db.query(Teacher).first() is not None:
            print("数据已存在，跳过初始化")
            db.close()
            return
        
        # 创建老师
        teacher = Teacher(account="T001", name="张老师")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        
        # 班级列表
        classes = ["计算机2201班", "计算机2202班", "计算机2203班"]
        
        # 考试类型
        exam_types = ["第一次考试", "第二次考试", "第三次考试", "期中考试", "期末考试"]
        
        # 为每个班级创建所有考试场次
        for class_name in classes:
            for exam_name in exam_types:
                exam = Exam(
                    name=exam_name,
                    class_name=class_name,
                    teacher_id=teacher.id,
                    total_score=100
                )
                db.add(exam)
        
        # 创建示例学生
        students_data = [
            ("S2201001", "李明", "计算机2201班"),
            ("S2201002", "王芳", "计算机2201班"),
            ("S2201003", "张伟", "计算机2201班"),
            ("S2202001", "刘洋", "计算机2202班"),
            ("S2202002", "陈静", "计算机2202班"),
            ("S2202003", "赵强", "计算机2202班"),
            ("S2203001", "孙华", "计算机2203班"),
            ("S2203002", "周琳", "计算机2203班"),
            ("S2203003", "吴涛", "计算机2203班"),
        ]
        
        for account, name, class_name in students_data:
            student = Student(account=account, name=name, class_name=class_name)
            db.add(student)
        
        db.commit()
        print("初始数据创建完成")
        db.close()
    except Exception as e:
        print(f"初始化数据失败: {e}")
        try:
            db.close()
        except:
            pass


# 在模块加载时初始化（不使用 lifespan）
print("=" * 50)
print("初始化数据库...")
init_db()
print("数据库初始化完成")
init_sample_data()
print(f"数据目录: {DATA_DIR}")
print("=" * 50)

# 创建FastAPI应用
app = FastAPI(
    title="试卷批改系统",
    description="支持学生上传试卷自动批改，老师查看班级整体成绩报告",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(router)


@app.get("/reports/{file_path:path}")
async def serve_report(file_path: str):
    """服务报告文件"""
    full_path = os.path.join(REPORTS_DIR, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(full_path)
    return JSONResponse(status_code=404, content={"detail": "报告文件不存在"})


@app.get("/uploads/{file_path:path}")
async def serve_upload(file_path: str):
    """服务上传文件"""
    full_path = os.path.join(UPLOADS_DIR, file_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(full_path)
    return JSONResponse(status_code=404, content={"detail": "文件不存在"})


@app.get("/")
async def root():
    """根路由 - 返回前端页面"""
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "试卷批改系统 API 服务运行中"}


# SPA fallback
@app.get("/{path:path}")
async def serve_frontend(path: str):
    """服务前端静态文件"""
    file_path = os.path.join(FRONTEND_DIST, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return JSONResponse(status_code=404, content={"error": "Not found"})
