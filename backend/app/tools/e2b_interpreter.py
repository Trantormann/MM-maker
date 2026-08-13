"""E2B 云端代码解释器模块。"""

from app.tools.base_interpreter import BaseCodeInterpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.utils.log_util import logger


class E2BCodeInterpreter(BaseCodeInterpreter):
    """基于 E2B 云端的代码解释器。"""

    def __init__(
        self,
        task_id: str,
        work_dir: str,
        notebook_serializer: NotebookSerializer,
        api_key: str | None = None,
    ):
        super().__init__(task_id, work_dir, notebook_serializer)
        self.api_key = api_key
        self.sandbox = None

    async def initialize(self):
        """初始化 E2B 沙盒。"""
        try:
            from e2b_code_interpreter import Sandbox

            self.sandbox = Sandbox(api_key=self.api_key)
            logger.info("E2B 沙盒初始化完成")
        except Exception as e:
            logger.error(f"E2B 沙盒初始化失败: {e}")
            raise

    async def _pre_execute_code(self):
        """执行初始化代码。"""
        pass

    async def execute_code(self, code: str) -> tuple[str, bool, str]:
        """在 E2B 沙盒中执行代码。"""
        if not self.sandbox:
            return "", True, "E2B 沙盒未初始化"

        try:
            execution = self.sandbox.run_code(code)
            text_to_gpt = execution.text
            error_occurred = execution.error is not None
            error_message = str(execution.error) if execution.error else ""

            self.notebook_serializer.add_code_cell_to_notebook(code)
            if text_to_gpt:
                self.notebook_serializer.add_code_cell_output_to_notebook(text_to_gpt)
            if error_occurred:
                self.notebook_serializer.add_code_cell_error_to_notebook(error_message)

            return text_to_gpt, error_occurred, error_message

        except Exception as e:
            logger.error(f"E2B 代码执行失败: {e}")
            return "", True, str(e)

    async def get_created_images(self, section: str) -> list[str]:
        """获取创建的图片列表。"""
        # E2B 模式下需要下载文件
        return []

    async def cleanup(self):
        """清理 E2B 沙盒资源。"""
        if self.sandbox:
            self.sandbox.kill()
            logger.info("E2B 沙盒已关闭")
