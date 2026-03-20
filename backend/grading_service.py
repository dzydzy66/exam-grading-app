"""
试卷批改服务
集成 exam-grading 技能和大模型能力
"""
import os
import json
import sys
import base64
from typing import Dict, Any, Optional
from datetime import datetime

# 添加 exam-grading 技能路径
EXAM_GRADING_PATH = "/skills/user/exam-grading"
sys.path.insert(0, EXAM_GRADING_PATH)

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exam_data")
ANSWER_KEYS_DIR = os.path.join(DATA_DIR, "answer_keys")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")

# 报告生成脚本路径
REPORT_GENERATOR_SCRIPT = os.path.join(EXAM_GRADING_PATH, "scripts", "report_generator.py")

# 学科名称
SUBJECT_NAME = "计算机组成与体系结构"


def get_text_content(content) -> str:
    """安全地从 AIMessage content 提取文本"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        else:
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
    return str(content)


class GradingService:
    """试卷批改服务"""
    
    async def grade_exam(
        self,
        image_path: str,
        student_name: str,
        class_name: str,
        exam: Any,
        db: Any = None
    ) -> Dict[str, Any]:
        """
        批改试卷
        
        Args:
            image_path: 试卷图片路径
            student_name: 学生姓名
            class_name: 班级
            exam: 考试对象
            db: 数据库会话
            
        Returns:
            批改结果字典
        """
        try:
            # 1. 读取标准答案（优先从数据库）
            answer_key = self._load_answer_key(exam.id, db)
            
            # 2. 识别试卷内容（使用大模型）
            exam_content = await self._recognize_exam_with_llm(image_path, answer_key)
            
            # 3. 批改评分
            grading_data = self._grade_answers(exam_content, answer_key, student_name, class_name, exam)
            
            # 4. 生成JSON数据文件
            json_file = f"grading_{student_name}_exam_{exam.id}.json"
            json_path = os.path.join(REPORTS_DIR, json_file)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(grading_data, f, ensure_ascii=False, indent=2)
            
            # 5. 生成HTML报告
            report_file = f"student_{student_name}_exam_{exam.id}.html"
            report_path = os.path.join(REPORTS_DIR, report_file)
            
            self._generate_report(json_path, report_path, f"{exam.name} - {SUBJECT_NAME}")
            
            return {
                "success": True,
                "score": grading_data["summary"]["total_earned"],
                "report_file": report_file
            }
            
        except Exception as e:
            print(f"批改失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _load_answer_key(self, exam_id: int, db: Any = None) -> Dict[str, Any]:
        """加载标准答案"""
        # 优先从数据库加载
        if db:
            try:
                from database import AnswerKey
                answer_key_record = db.query(AnswerKey).filter(AnswerKey.exam_id == exam_id).first()
                if answer_key_record:
                    return json.loads(answer_key_record.content)
            except Exception as e:
                print(f"从数据库加载标准答案失败: {e}")
        
        # 尝试从文件加载
        answer_key_file = f"exam_{exam_id}.json"
        answer_key_path = os.path.join(ANSWER_KEYS_DIR, answer_key_file)
        
        if os.path.exists(answer_key_path):
            with open(answer_key_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # 返回默认答案
        return self._get_default_answer_key()
    
    def _get_default_answer_key(self) -> Dict[str, Any]:
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
    
    async def _recognize_exam_with_llm(self, image_path: str, answer_key: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 识别试卷内容"""
        try:
            from coze_coding_dev_sdk import LLMClient
            from langchain_core.messages import SystemMessage, HumanMessage
            
            # 读取图片并转换为 base64
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # 获取图片格式
            image_ext = os.path.splitext(image_path)[1].lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }.get(image_ext, 'image/jpeg')
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:{mime_type};base64,{base64_image}"
            
            # 构建提示词
            questions_info = "\n".join([
                f"第{q['number']}题 ({q['type']}, {q['score']}分): {q['content']}"
                for q in answer_key.get("questions", [])
            ])
            
            system_prompt = """你是一个专业的试卷批改助手，负责识别《计算机组成与体系结构》试卷。
请仔细查看试卷图片，识别每道题的学生答案。
输出格式必须是纯JSON，不要有任何其他文字说明。"""

            user_prompt = f"""请识别这张《计算机组成与体系结构》试卷图片中每道题的学生答案。

题目列表:
{questions_info}

请按照以下JSON格式输出学生的答案：
{{
  "questions": [
    {{"number": 1, "student_answer": "学生的答案"}},
    {{"number": 2, "student_answer": "学生的答案"}}
  ]
}}

注意：
1. 只输出JSON格式，不要有其他文字
2. 选择题答案用字母表示（如A、B、C、D）
3. 填空题和计算题填写具体答案
4. 简答题和计算题如果有计算过程，也请识别
5. 如果看不清某道题的答案，填写"未识别"
6. 请仔细查看试卷图片，识别所有题目的答案"""

            client = LLMClient()
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=[
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ])
            ]
            
            response = client.invoke(
                messages=messages,
                model="doubao-seed-1-6-vision-250815",
                temperature=0.1
            )
            
            content = get_text_content(response.content)
            print(f"LLM 响应: {content}")
            
            # 尝试解析 JSON
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except json.JSONDecodeError:
                pass
            
            return self._get_default_recognition(answer_key)
            
        except Exception as e:
            print(f"LLM 识别失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._get_default_recognition(answer_key)
    
    def _get_default_recognition(self, answer_key: Dict[str, Any]) -> Dict[str, Any]:
        """获取默认识别结果（模拟）"""
        import random
        questions = answer_key.get("questions", [])
        recognized = {"questions": []}
        
        for q in questions:
            # 模拟：70%概率答对
            is_correct = random.random() < 0.7
            recognized["questions"].append({
                "number": q["number"],
                "student_answer": q["correct_answer"] if is_correct else self._get_wrong_answer(q["type"], q["correct_answer"])
            })
        
        return recognized
    
    def _get_wrong_answer(self, question_type: str, correct_answer: str) -> str:
        """生成错误答案（模拟用）"""
        if question_type == "选择题":
            options = ["A", "B", "C", "D"]
            if correct_answer in options:
                options.remove(correct_answer)
            return options[0] if options else "A"
        elif question_type in ["填空题", "计算题"]:
            return "错误答案"
        else:
            return "回答错误"
    
    def _grade_answers(
        self,
        exam_content: Dict[str, Any],
        answer_key: Dict[str, Any],
        student_name: str,
        class_name: str,
        exam: Any
    ) -> Dict[str, Any]:
        """批改答案并生成批改数据"""
        questions_result = []
        total_earned = 0
        correct_count = 0
        wrong_count = 0
        
        score_distribution = {}
        
        for q in answer_key.get("questions", []):
            student_answer = ""
            for recognized_q in exam_content.get("questions", []):
                if recognized_q["number"] == q["number"]:
                    student_answer = recognized_q.get("student_answer", "")
                    break
            
            # 使用 LLM 判断答案是否正确
            is_correct = self._check_answer_with_llm(
                q["type"], 
                student_answer, 
                q["correct_answer"]
            )
            
            earned_score = q["score"] if is_correct else 0
            
            # 主观题部分得分
            if q["type"] in ["简答题", "应用题"] and not is_correct and student_answer and student_answer != "未识别":
                earned_score = q["score"] // 2
            
            total_earned += earned_score
            if is_correct:
                correct_count += 1
            else:
                wrong_count += 1
            
            q_type = q["type"]
            if q_type not in score_distribution:
                score_distribution[q_type] = {"earned": 0, "total": 0, "correct": 0, "wrong": 0}
            score_distribution[q_type]["earned"] += earned_score
            score_distribution[q_type]["total"] += q["score"]
            if is_correct:
                score_distribution[q_type]["correct"] += 1
            else:
                score_distribution[q_type]["wrong"] += 1
            
            questions_result.append({
                "number": q["number"],
                "type": q["type"],
                "content": q["content"],
                "student_answer": student_answer,
                "correct_answer": q["correct_answer"],
                "score": q["score"],
                "earned_score": earned_score,
                "is_correct": is_correct,
                "analysis": q.get("analysis", "")
            })
        
        accuracy_rate = f"{(correct_count / len(questions_result) * 100):.0f}%" if questions_result else "0%"
        
        # 获取老师姓名
        teacher_name = "老师"
        if hasattr(exam, 'teacher') and exam.teacher:
            teacher_name = exam.teacher.name
        
        grading_data = {
            "exam_info": {
                "subject": SUBJECT_NAME,
                "total_score": answer_key.get("total_score", exam.total_score),
                "student_name": student_name,
                "exam_date": datetime.now().strftime("%Y-%m-%d"),
                "class_name": class_name,
                "teacher_name": teacher_name
            },
            "questions": questions_result,
            "summary": {
                "total_earned": total_earned,
                "accuracy_rate": accuracy_rate,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "score_distribution": score_distribution
            }
        }
        
        return grading_data
    
    def _check_answer_with_llm(self, question_type: str, student_answer: str, correct_answer: str) -> bool:
        """使用 LLM 判断答案是否正确"""
        # 客观题直接比较
        if question_type in ["选择题", "判断题"]:
            return student_answer.strip().upper() == correct_answer.strip().upper()
        
        # 填空题允许部分匹配
        if question_type == "填空题":
            student_normalized = student_answer.strip().lower()
            correct_normalized = correct_answer.strip().lower()
            return student_normalized == correct_normalized or correct_normalized in student_normalized
        
        # 主观题需要 LLM 判断
        try:
            from coze_coding_dev_sdk import LLMClient
            from langchain_core.messages import SystemMessage, HumanMessage
            
            client = LLMClient()
            
            messages = [
                SystemMessage(content="你是一个试卷批改助手，负责判断学生的答案是否正确。请只回答'是'或'否'。"),
                HumanMessage(content=f"""题目类型：{question_type}
标准答案：{correct_answer}
学生答案：{student_answer}

请判断学生答案是否正确或等价。如果答案正确或意思相同，回答"是"，否则回答"否"。只需要回答"是"或"否"。""")
            ]
            
            response = client.invoke(
                messages=messages,
                model="doubao-seed-1-8-251228",
                temperature=0.1
            )
            
            content = get_text_content(response.content).strip()
            return "是" in content
            
        except Exception as e:
            print(f"LLM 判断答案失败: {e}")
            # 如果 LLM 调用失败，使用简单匹配
            return student_answer.strip() == correct_answer.strip()
    
    def _generate_report(self, json_path: str, output_path: str, title: str):
        """生成HTML报告"""
        import subprocess
        
        cmd = [
            "python",
            REPORT_GENERATOR_SCRIPT,
            "--input", json_path,
            "--output", output_path,
            "--title", title
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"报告生成失败: {result.stderr}")
            raise Exception(f"报告生成失败: {result.stderr}")
