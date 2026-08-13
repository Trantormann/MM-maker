"""代码解释器工厂模块。"""

from app.config.setting import settings
from app.tools.base_interpreter import BaseCodeInterpreter
from app.tools.e2b_interpreter import E2BCodeInterpreter
from app.tools.local_interpreter import LocalCodeInterpreter
from app.tools.notebook_serializer import NotebookSerializer


async def create_interpreter(
    kind: str,
    task_id: str,
    work_dir: str,
    notebook_serializer: NotebookSerializer,
    timeout: int = 3000,
) -> BaseCodeInterpreter:
    """创建代码解释器实例。

    Args:
        kind: 解释器类型（local | e2b）。
        task_id: 任务 ID。
        work_dir: 工作目录。
        notebook_serializer: Notebook 序列化器。
        timeout: 超时时间（秒）。

    Returns:
        代码解释器实例。
    """
    if kind == "e2b":
        interpreter = E2BCodeInterpreter(
            task_id=task_id,
            work_dir=work_dir,
            notebook_serializer=notebook_serializer,
            api_key=settings.E2B_API_KEY,
        )
    else:
        interpreter = LocalCodeInterpreter(
            task_id=task_id,
            work_dir=work_dir,
            notebook_serializer=notebook_serializer,
        )

    await interpreter.initialize()
    return interpreter
