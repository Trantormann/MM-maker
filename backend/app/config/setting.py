"""应用配置模块，基于 pydantic-settings 管理环境变量和全局配置。"""

import os
from enum import Enum
from typing import Annotated

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiType(str, Enum):
    """LLM API 类型。"""

    OPENAI_CHAT = "openai-chat"
    OPENAI_RESPONSES = "openai-responses"
    ANTHROPIC = "anthropic"


def parse_cors(value: str) -> list[str]:
    """将 CORS 配置字符串解析为 URL 列表。"""
    if value == "*":
        return ["*"]
    if "," in value:
        return [url.strip() for url in value.split(",")]
    return [value]


class Settings(BaseSettings):
    """全局应用配置，从环境变量和 .env 文件加载。"""

    ENV: str = "dev"

    # ---- 协调者配置 ----
    COORDINATOR_API_TYPE: ApiType | None = None
    COORDINATOR_API_KEY: str | None = None
    COORDINATOR_MODEL: str | None = None
    COORDINATOR_BASE_URL: str | None = None
    COORDINATOR_MAX_TOKENS: int | None = None
    COORDINATOR_CONTEXT_WINDOW: int = 128000

    # ---- 建模手配置 ----
    MODELER_API_TYPE: ApiType | None = None
    MODELER_API_KEY: str | None = None
    MODELER_MODEL: str | None = None
    MODELER_BASE_URL: str | None = None
    MODELER_MAX_TOKENS: int | None = None
    MODELER_CONTEXT_WINDOW: int = 128000

    # ---- 代码手配置 ----
    CODER_API_TYPE: ApiType | None = None
    CODER_API_KEY: str | None = None
    CODER_MODEL: str | None = None
    CODER_BASE_URL: str | None = None
    CODER_MAX_TOKENS: int | None = None
    CODER_CONTEXT_WINDOW: int = 128000

    # ---- 写作手配置 ----
    WRITER_API_TYPE: ApiType | None = None
    WRITER_API_KEY: str | None = None
    WRITER_MODEL: str | None = None
    WRITER_BASE_URL: str | None = None
    WRITER_MAX_TOKENS: int | None = None
    WRITER_CONTEXT_WINDOW: int = 128000

    # ---- 评审手配置 ----
    REVIEWER_API_TYPE: ApiType | None = None
    REVIEWER_API_KEY: str | None = None
    REVIEWER_MODEL: str | None = None
    REVIEWER_BASE_URL: str | None = None
    REVIEWER_MAX_TOKENS: int | None = None
    REVIEWER_CONTEXT_WINDOW: int = 128000

    # ---- 执行限制 ----
    MAX_CHAT_TURNS: int | None = None
    MAX_RETRIES: int | None = None

    # ---- 代码沙盒 ----
    E2B_API_KEY: str | None = None
    CODE_INTERPRETER_KIND: str = "local"  # local | e2b
    JUPYTER_KERNEL_NAME: str = "python3"  # 本地 Jupyter 内核名

    # ---- 文献检索 ----
    OPENALEX_EMAIL: str | None = None
    OPENALEX_API_KEY: str | None = None

    # ---- Redis ----
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 10

    # ---- 服务器 ----
    SERVER_HOST: str = "http://localhost:8000"
    CORS_ALLOW_ORIGINS: Annotated[list[str] | str, BeforeValidator(parse_cors)] = "*"

    # ---- 日志 ----
    LOG_LEVEL: str = "DEBUG"
    DEBUG: bool = True

    # ---- HIL 人机协作 ----
    HIL_ENABLED: bool = False
    HIL_TIMEOUT: int = 300  # 审批超时时间（秒）
    HIL_CHECKPOINTS: dict = {
        "problem_split": False,     # 问题拆解后确认
        "model_selection": False,   # 模型选择确认
        "code_review": False,       # 代码审查
        "paper_review": False,      # 论文评审
        "final_review": False,      # 最终确认
    }

    # ---- 质量反馈 ----
    FEEDBACK_ENABLED: bool = True
    FEEDBACK_MAX_ITERATIONS: int = 3  # 最大反馈迭代次数
    FEEDBACK_SCORE_THRESHOLD: float = 7.0  # 评分阈值（满分10分）

    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        extra="allow",
    )

    @classmethod
    def from_env(cls, env: str | None = None) -> "Settings":
        """根据环境名称加载对应配置。"""
        env = env or os.getenv("ENV", "dev")
        env_file = f".env.{env.lower()}"
        return cls(_env_file=env_file, _env_file_encoding="utf-8")  # type: ignore[call-arg]


settings = Settings()
