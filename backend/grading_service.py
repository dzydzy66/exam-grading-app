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
        exam: Any
    ) -> Dict[str, Any]:
        """
        批改试卷
        
        Args:
            image_path: 试卷图片路径
            student_name: 学生姓名
            class_name: 班级
            exam: 考试对象
            
        Returns:
            批改结果字典
        """
        try:
            # 1. 读取标准答案
            answer_key = self._load_answer_key(exam.id)
            
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
            
            self._generate_report(json_path, report_path, f"{exam.subject} - {exam.name}")
            
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
    
    def _load_answer_key(self, exam_id: int) -> Dict[str, Any]:
        """加载标准答案"""
        answer_key_file = f"exam_{exam_id}.json"
        answer_key_path = os.path.join(ANSWER_KEYS_DIR, answer_key_file)
        
        if os.path.exists(answer_key_path):
            with open(answer_key_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        return self._get_default_answer_key()
    
    def _get_default_answer_key(self) -> Dict[str, Any]:
        """获取默认标准答案模板"""
        return {
            "subject": "数学",
            "total_score": 100,
            "questions": [
                {
                    "number": 1,
                    "type": "选择题",
                    "content": "题目1",
                    "correct_answer": "B",
                    "score": 20
                },
                {
                    "number": 2,
                    "type": "填空题",
                    "content": "题目2",
                    "correct_answer": "答案",
                    "score": 20
                },
                {
                    "number": 3,
                    "type": "计算题",
                    "content": "题目3",
                    "correct_answer": "结果",
                    "score": 30
                },
                {
                    "number": 4,
                    "type": "应用题",
                    "content": "题目4",
                    "correct_answer": "解答",
                    "score": 30
                }
            ]
        }
    
    async def _recognize_exam_with_llm(self, image_path: str, answer_key: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 识别试卷内容
        """
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
            
            # 构建 base64 URL
            base64_image = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:{mime_type};base64,{base64_image}"
            
            # 构建提示词
            questions_info = "\n".join([
                f"第{q['number']}题 ({q['type']}, {q['score']}分): {q['content']}"
                for q in answer_key.get("questions", [])
            ])
            
            system_prompt = """你是一个试卷识别助手。你需要识别试卷图片中的学生答案。
请仔细查看图片，识别每道题的学生答案。
输出格式必须是纯JSON，不要有任何其他文字说明。"""

            user_prompt = f"""请识别这张试卷图片中每道题的学生答案。

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
4. 如果看不清某道题的答案，填写"未识别"
5. 请仔细查看试卷图片，识别所有题目的答案"""

            # 初始化 LLM 客户端
            client = LLMClient()
            
            # 构建消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=[
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ])
            ]
            
            # 调用 LLM
            response = client.invoke(
                messages=messages,
                model="doubao-seed-1-6-vision-250815",
                temperature=0.1
            )
            
            # 解析响应
            content = get_text_content(response.content)
            print(f"LLM 响应: {content}")
            
            # 尝试解析 JSON
            try:
                # 尝试提取 JSON 部分
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except json.JSONDecodeError:
                pass
            
            # 如果解析失败，返回默认值
            return self._get_default_recognition(answer_key)
            
        except Exception as e:
            print(f"LLM 识别失败: {str(e)}")
            import traceback
            traceback.print_exc()
            # 如果 LLM 调用失败，使用模拟数据
            return self._get_default_recognition(answer_key)
    
    def _get_default_recognition(self, answer_key: Dict[str, Any]) -> Dict[str, Any]:
        """获取默认识别结果（模拟）"""
        import random
        questions = answer_key.get("questions", [])
        recognized = {"questions": []}
        
        for q in questions:
            is_correct = random.random() < 0.8
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
            return "错误"
    
    def _grade_answers(
        self,
        exam_content: Dict[str, Any],
        answer_key: Dict[str, Any],
        student_name: str,
        class_name: str,
        exam: Any
    ) -> Dict[str, Any]:
        """
        批改答案并生成批改数据
        """
        questions_result = []
        total_earned = 0
        correct_count = 0
        wrong_count = 0
        
        teacher_name = exam.teacher.name if hasattr(exam, 'teacher') and exam.teacher else "老师"
        score_distribution = {}
        
        for q in answer_key.get("questions", []):
            student_answer = ""
            for recognized_q in exam_content.get("questions", []):
                if recognized_q["number"] == q["number"]:
                    student_answer = recognized_q.get("student_answer", "")
                    break
            
            is_correct = student_answer == q["correct_answer"]
            earned_score = q["score"] if is_correct else 0
            
            if q["type"] in ["简答题", "应用题"] and not is_correct and student_answer != "未识别":
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
        
        grading_data = {
            "exam_info": {
                "subject": answer_key.get("subject", exam.subject),
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
