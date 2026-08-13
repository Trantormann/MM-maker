"""Agent 间通信数据模型定义。"""

from typing import Any

from pydantic import BaseModel


class CoordinatorToModeler(BaseModel):
    """协调者传递给建模手的数据结构。"""

    questions: dict
    ques_count: int


class ModelerToCoder(BaseModel):
    """建模手传递给代码手的数据结构。"""

    questions_solution: dict[str, str]


class CoderToWriter(BaseModel):
    """代码手传递给写作手的数据结构。"""

    code_response: str | None = None
    code_output: str | None = None
    created_images: list[str] | None = None


class WriterResponse(BaseModel):
    """写作手的响应数据结构。"""

    response_content: Any
    footnotes: list[tuple[str, str]] | None = None


class ReviewResult(BaseModel):
    """评审结果数据结构。"""

    score: float                    # 总分 (0-10)
    dimension_scores: dict[str, float]  # 各维度得分
    feedback: str                   # 详细反馈
    suggestions: list[str]          # 改进建议
    needs_revision: bool            # 是否需要修改
    revision_areas: list[str]       # 需要修改的部分


class HILCheckpoint(BaseModel):
    """人机协作检查点数据。"""

    checkpoint_id: str
    stage: str                      # 当前阶段
    content: dict                   # 待审批内容
    action: str | None = None       # 用户决策
    feedback: str | None = None     # 用户反馈
