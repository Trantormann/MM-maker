"""响应数据模型定义。"""

from typing import Any

from pydantic import BaseModel


class SystemMessage(BaseModel):
    """系统消息。"""

    content: str
    type: str = "info"  # info | success | warning | error


class CoordinatorMessage(BaseModel):
    """协调者消息。"""

    content: str


class ModelerMessage(BaseModel):
    """建模手消息。"""

    content: str


class CoderMessage(BaseModel):
    """代码手消息。"""

    content: str


class WriterMessage(BaseModel):
    """写作手消息。"""

    content: str


class ReviewerMessage(BaseModel):
    """评审手消息。"""

    content: str
    score: float | None = None


class OutputItem(BaseModel):
    """输出项基类。"""

    res_type: str
    format: str
    msg: str


class ResultModel(OutputItem):
    """执行结果。"""

    res_type: str = "result"


class StdErrModel(OutputItem):
    """错误输出。

    继承 OutputItem 以兼容 InterpreterMessage.output 的 list[OutputItem] 类型，
    否则代码执行出错时构造 InterpreterMessage 会抛 pydantic ValidationError，
    导致真实错误信息被覆盖，代码手无法据此修复。
    """

    res_type: str = "stderr"
    format: str = "text"


class InterpreterMessage(BaseModel):
    """代码解释器消息。"""

    input: dict | None = None
    output: list[OutputItem] | None = None


class HILCheckpointMessage(BaseModel):
    """HIL 检查点消息。"""

    checkpoint_id: str
    stage: str
    content: dict
    timeout: int = 300


class TaskStatusMessage(BaseModel):
    """任务状态消息。"""

    task_id: str
    status: str
    progress: float  # 0-100
    current_stage: str
    message: str
