"""
试卷批改系统 - FastAPI 主程序
"""
import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 添加后端目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db
from routes import router

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

# 注册路由
app.include_router(router)

# 静态文件目录
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exam_data")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

# 挂载静态文件
if os.path.exists(REPORTS_DIR):
    app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")
if os.path.exists(UPLOADS_DIR):
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    # 初始化数据库
    init_db()
    print("数据库初始化完成")


@app.get("/")
async def root():
    """根路由 - 返回前端页面"""
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "试卷批改系统 API 服务运行中，请访问前端页面"}


@app.get("/{path:path}")
async def serve_frontend(path: str):
    """服务前端静态文件"""
    # 检查是否是API路由
    if path.startswith("api/"):
        return None
    
    # 尝试返回前端文件
    file_path = os.path.join(FRONTEND_DIST, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # 返回index.html（SPA路由）
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return {"error": "Not found"}


if __name__ == "__main__":
    # 获取端口
    port = int(os.environ.get("DEPLOY_RUN_PORT", 5000))
    
    print(f"启动服务器，端口: {port}")
    print(f"访问地址: http://localhost:{port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
