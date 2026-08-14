"""本地代码解释器模块，通过本地 Jupyter 内核执行 Python 代码。"""

import os

import jupyter_client

from app.config.setting import settings
from app.schemas.response import OutputItem, ResultModel, StdErrModel, SystemMessage
from app.services.redis_manager import redis_manager
from app.tools.base_interpreter import BaseCodeInterpreter
from app.tools.matplotlib_setup import build_matplotlib_init_code
from app.tools.notebook_serializer import NotebookSerializer
from app.utils.log_util import logger


class LocalCodeInterpreter(BaseCodeInterpreter):
    """基于本地 Jupyter 内核的代码解释器。"""

    def __init__(
        self,
        task_id: str,
        work_dir: str,
        notebook_serializer: NotebookSerializer,
    ):
        super().__init__(task_id, work_dir, notebook_serializer)
        self.km, self.kc = None, None
        self.interrupt_signal = False

    async def initialize(self):
        """初始化 Jupyter 内核。"""
        logger.info(f"初始化本地内核（{settings.JUPYTER_KERNEL_NAME}）")
        kernel_env = os.environ.copy()
        kernel_env["PYTHONIOENCODING"] = "utf-8"
        kernel_env["PYTHONUTF8"] = "1"
        self.km, self.kc = jupyter_client.manager.start_new_kernel(
            kernel_name=settings.JUPYTER_KERNEL_NAME, env=kernel_env
        )
        font_msg, font_type = self._pre_execute_code()
        if font_msg:
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content=font_msg, type=font_type),
            )

    def _pre_execute_code(self) -> tuple[str | None, str]:
        """执行 matplotlib 初始化，并解析字体加载结果。"""
        init_code = build_matplotlib_init_code(self.work_dir)
        execution = self.execute_code_(init_code)
        stdout = "\n".join(text for mark, text in execution if mark == "stdout")
        for line in stdout.splitlines():
            line = line.strip()
            if "中文字体已加载" in line:
                content = line.removeprefix("[matplotlib_setup] ").strip()
                return content, "success"
            if "未找到中文字体" in line:
                content = line.removeprefix("[matplotlib_setup] ").strip()
                return content, "warning"
        return None, "info"

    async def execute_code(self, code: str) -> tuple[str, bool, str]:
        """执行 Python 代码。

        Args:
            code: 要执行的 Python 代码。

        Returns:
            (输出文本, 是否出错, 错误信息) 元组。
        """
        logger.info(f"执行代码: {code[:200]}...")
        self.notebook_serializer.add_code_cell_to_notebook(code)

        text_to_gpt: list[str] = []
        content_to_display: list[OutputItem] | None = []
        error_occurred: bool = False
        error_message: str = ""

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="开始执行代码"),
        )

        execution = self.execute_code_(code)

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="代码执行完成"),
        )

        for mark, out_str in execution:
            if mark in ("stdout", "execute_result_text", "display_text"):
                text_to_gpt.append(self._truncate_text(f"[{mark}]\n{out_str}"))
                content_to_display.append(
                    ResultModel(res_type="result", format="text", msg=out_str)
                )
                self.notebook_serializer.add_code_cell_output_to_notebook(out_str)

            elif mark in (
                "execute_result_png",
                "execute_result_jpeg",
                "display_png",
                "display_jpeg",
            ):
                text_to_gpt.append(f"[{mark} 图片已生成，内容为 base64，未展示]")
                if "png" in mark:
                    self.notebook_serializer.add_image_to_notebook(out_str, "image/png")
                    content_to_display.append(
                        ResultModel(res_type="result", format="png", msg=out_str)
                    )
                else:
                    self.notebook_serializer.add_image_to_notebook(out_str, "image/jpeg")
                    content_to_display.append(
                        ResultModel(res_type="result", format="jpeg", msg=out_str)
                    )
                # 将 base64 图片保存为磁盘文件，供写作手引用
                self._save_image_file(out_str, mark)

            elif mark == "error":
                error_occurred = True
                error_message = self.delete_color_control_char(out_str)
                error_message = self._truncate_text(error_message)
                logger.error(f"执行错误: {error_message}")
                text_to_gpt.append(error_message)
                self.notebook_serializer.add_code_cell_error_to_notebook(out_str)
                content_to_display.append(StdErrModel(msg=out_str))

        combined_text = "\n".join(text_to_gpt)
        # 将本 section 的输出记录下来，供写作手 prompt 引用
        if combined_text and self.current_section:
            self.add_content(self.current_section, combined_text)
        await self._push_to_websocket(content_to_display)

        return combined_text, error_occurred, error_message

    def _save_image_file(self, base64_data: str, mark: str) -> None:
        """将 base64 图片数据保存为磁盘文件。

        Args:
            base64_data: base64 编码的图片数据。
            mark: 输出类型标记，用于确定文件扩展名。
        """
        try:
            import base64 as b64
            import uuid

            figures_dir = os.path.join(self.work_dir, "figures")
            os.makedirs(figures_dir, exist_ok=True)

            ext = "png" if "png" in mark else "jpg"
            filename = f"{uuid.uuid4().hex[:12]}.{ext}"
            filepath = os.path.join(figures_dir, filename)

            image_bytes = b64.b64decode(base64_data)
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            logger.info(f"图片已保存: {filename}")
        except Exception as e:
            logger.error(f"保存图片失败: {e}")

    def execute_code_(self, code: str) -> list[tuple[str, str]]:
        """在 Jupyter 内核中执行代码并收集输出。

        Args:
            code: 要执行的 Python 代码。

        Returns:
            (输出类型, 输出内容) 元组列表。
        """
        assert self.kc is not None
        assert self.km is not None
        self.kc.execute(code)

        msg_list = []
        while True:
            try:
                iopub_msg = self.kc.get_iopub_msg(timeout=1)
                msg_list.append(iopub_msg)
                if (
                    iopub_msg["msg_type"] == "status"
                    and iopub_msg["content"].get("execution_state") == "idle"
                ):
                    break
            except Exception:
                if self.interrupt_signal:
                    self.km.interrupt_kernel()
                    self.interrupt_signal = False
                continue

        all_output: list[tuple[str, str]] = []
        for iopub_msg in msg_list:
            if iopub_msg["msg_type"] == "stream":
                if iopub_msg["content"].get("name") == "stdout":
                    all_output.append(("stdout", iopub_msg["content"]["text"]))
            elif iopub_msg["msg_type"] == "execute_result":
                if "data" in iopub_msg["content"]:
                    data = iopub_msg["content"]["data"]
                    if "text/plain" in data:
                        all_output.append(("execute_result_text", data["text/plain"]))
                    if "image/png" in data:
                        all_output.append(("execute_result_png", data["image/png"]))
                    if "image/jpeg" in data:
                        all_output.append(("execute_result_jpeg", data["image/jpeg"]))
            elif iopub_msg["msg_type"] == "display_data":
                if "data" in iopub_msg["content"]:
                    data = iopub_msg["content"]["data"]
                    if "text/plain" in data:
                        all_output.append(("display_text", data["text/plain"]))
                    if "image/png" in data:
                        all_output.append(("display_png", data["image/png"]))
                    if "image/jpeg" in data:
                        all_output.append(("display_jpeg", data["image/jpeg"]))
            elif iopub_msg["msg_type"] == "error":
                error_text = "\n".join(iopub_msg["content"].get("traceback", []))
                all_output.append(("error", error_text))

        return all_output

    async def get_created_images(self, section: str) -> list[str]:
        """获取当前 section 新增的图片列表。

        扫描工作目录及其子目录下的所有图片文件，
        与本 section 开始前已记录的图片集合做差集，
        返回相对 work_dir 的路径，供写作手在论文中引用。

        Args:
            section: 当前章节名称。

        Returns:
            本 section 新增图片的相对路径列表。
        """
        image_exts = (".png", ".jpg", ".jpeg", ".svg")
        all_images: set[str] = set()

        for root, _, filenames in os.walk(self.work_dir):
            for f in filenames:
                if f.lower().endswith(image_exts):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, self.work_dir).replace(os.sep, "/")
                    all_images.add(rel_path)

        new_images = sorted(all_images - self.last_created_images)
        # 更新已记录图片集合，确保下一次调用只返回新增图片
        self.last_created_images = all_images
        return new_images

    async def cleanup(self):
        """清理资源，关闭 Jupyter 内核。"""
        logger.info("关闭本地内核")
        if self.kc:
            self.kc.stop_channels()
        if self.km:
            self.km.shutdown_kernel()
