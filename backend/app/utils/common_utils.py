"""通用工具函数模块。"""

import os
import re
import uuid
from datetime import datetime


def create_task_id() -> str:
    """生成唯一任务 ID。"""
    return str(uuid.uuid4())


def create_work_dir(task_id: str) -> str:
    """创建任务工作目录。"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dir_name = f"{timestamp}-{task_id[:8]}"
    work_dir = os.path.join("project", "work_dir", dir_name)
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(os.path.join(work_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(work_dir, "figures"), exist_ok=True)
    return work_dir


def get_current_files(work_dir: str, subdir: str = "data") -> str:
    """获取工作目录下的文件列表。"""
    target_dir = os.path.join(work_dir, subdir)
    if not os.path.exists(target_dir):
        return "无文件"
    files = []
    for f in os.listdir(target_dir):
        path = os.path.join(target_dir, f)
        size = os.path.getsize(path)
        files.append(f"- {f} ({size / 1024:.1f} KB)")
    return "\n".join(files) if files else "无文件"


def get_config_template(comp_template: str) -> dict:
    """获取竞赛模板配置。"""
    templates = {
        "CHINA": {
            "name": "全国大学生数学建模竞赛",
            "language": "中文",
            "sections": ["摘要", "问题重述", "问题分析", "模型假设", "符号说明", "模型建立与求解", "敏感性分析", "模型评价", "参考文献"],
        },
        "AMERICAN": {
            "name": "MCM/ICM",
            "language": "英文",
            "sections": ["Summary", "Introduction", "Problem Analysis", "Assumptions", "Model", "Results", "Sensitivity", "Evaluation", "References"],
        },
        "HUAWEI": {
            "name": "华为杯研究生数学建模竞赛",
            "language": "中文",
            "sections": ["摘要", "问题重述", "问题分析", "模型假设", "符号说明", "模型建立与求解", "敏感性分析", "模型评价", "参考文献"],
        },
    }
    return templates.get(comp_template, templates["CHINA"])


def md_2_docx(md_path: str, docx_path: str) -> bool:
    """将 Markdown 转换为 DOCX。"""
    try:
        import pypandoc
        pypandoc.convert_file(md_path, "docx", outputfile=docx_path)
        return True
    except Exception:
        return False


def transform_link(text: str) -> str:
    """转换文本中的链接格式。"""
    return text


def split_footnotes(text: str) -> tuple[str, list]:
    """分离文本中的脚注。"""
    footnotes = []
    pattern = r"\[\^(\d+)\]:\s*(.*?)(?=\n\[\^|\Z)"
    matches = re.findall(pattern, text, re.DOTALL)
    for num, content in matches:
        footnotes.append((num, content.strip()))
    text = re.sub(pattern, "", text, flags=re.DOTALL)
    return text, footnotes
