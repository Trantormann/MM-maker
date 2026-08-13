"""枚举类型定义模块。"""

from enum import Enum


class CompTemplate(str, Enum):
    """竞赛模板类型。"""

    CHINA = "CHINA"          # 国赛
    AMERICAN = "AMERICAN"    # 美赛 MCM/ICM
    HUAWEI = "HUAWEI"        # 华为杯
    HUASHU = "HUASHU"        # 华数杯


class FormatOutPut(str, Enum):
    """输出格式类型。"""

    Markdown = "Markdown"
    LaTeX = "LaTeX"


class AgentType(str, Enum):
    """Agent 类型标识。"""

    COORDINATOR = "CoordinatorAgent"
    MODELER = "ModelerAgent"
    CODER = "CoderAgent"
    WRITER = "WriterAgent"
    REVIEWER = "ReviewerAgent"
    SYSTEM = "SystemAgent"


class AgentStatus(str, Enum):
    """Agent 执行状态。"""

    START = "start"
    WORKING = "working"
    DONE = "done"
    ERROR = "error"
    SUCCESS = "success"


class HILAction(str, Enum):
    """人机协作决策动作。"""

    CONFIRM = "confirm"      # 确认继续
    EDIT = "edit"            # 编辑后继续
    REGENERATE = "regenerate"  # 重新生成
    ASK = "ask"              # 提问澄清
    SKIP = "skip"            # 跳过当前步骤
    ABORT = "abort"          # 中止任务


class ReviewScore(str, Enum):
    """评审等级。"""

    EXCELLENT = "excellent"  # 优秀 (9-10)
    GOOD = "good"            # 良好 (7-8)
    FAIR = "fair"            # 一般 (5-6)
    POOR = "poor"            # 较差 (3-4)
    BAD = "bad"              # 差 (0-2)
