"""Notebook 序列化模块，将代码执行过程保存为 Jupyter Notebook。"""

import os
from datetime import datetime

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from app.utils.log_util import logger


class NotebookSerializer:
    """将代码执行过程序列化为 Jupyter Notebook 文件。"""

    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.notebook = new_notebook()
        self.notebook.metadata = {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12",
            },
        }
        self._current_cell = None
        self._notebook_path = os.path.join(work_dir, "execution.ipynb")

    def add_markdown_cell(self, content: str) -> None:
        """添加 Markdown 单元格。"""
        cell = new_markdown_cell(content)
        self.notebook.cells.append(cell)
        self._save()

    def add_code_cell_to_notebook(self, code: str) -> None:
        """添加代码单元格。"""
        cell = new_code_cell(code)
        self.notebook.cells.append(cell)
        self._current_cell = cell
        self._save()

    def add_code_cell_output_to_notebook(self, output: str) -> None:
        """添加代码单元格的文本输出。"""
        if self._current_cell is None:
            return
        from nbformat.v4 import new_output
        out = new_output("stream", name="stdout", text=output)
        self._current_cell.outputs.append(out)
        self._save()

    def add_code_cell_error_to_notebook(self, error: str) -> None:
        """添加代码单元格的错误输出。"""
        if self._current_cell is None:
            return
        from nbformat.v4 import new_output
        out = new_output("stream", name="stderr", text=error)
        self._current_cell.outputs.append(out)
        self._save()

    def add_image_to_notebook(self, image_data: str, mime_type: str = "image/png") -> None:
        """添加图片输出到当前单元格。"""
        if self._current_cell is None:
            return
        from nbformat.v4 import new_output
        out = new_output(
            "display_data",
            data={mime_type: image_data},
        )
        self._current_cell.outputs.append(out)
        self._save()

    def _save(self) -> None:
        """保存 Notebook 到文件。"""
        try:
            with open(self._notebook_path, "w", encoding="utf-8") as f:
                nbformat.write(self.notebook, f)
        except Exception as e:
            logger.error(f"保存 Notebook 失败: {e}")

    def get_notebook_path(self) -> str:
        """获取 Notebook 文件路径。"""
        return self._notebook_path
