"""用户输出管理模块，负责论文结果的拼接、引用处理和保存。"""

import json
import os
import re
import uuid

from app.schemas.A2A import WriterResponse


class UserOutput:
    """管理建模任务的输出结果，处理引用编号、脚注和最终论文拼接。"""

    def __init__(self, work_dir: str, ques_count: int):
        self.work_dir = work_dir
        self.res: dict[str, dict] = {}
        self.cost_time = 0.0
        self.initialized = True
        self.ques_count: int = ques_count
        self.footnotes = {}
        self._init_seq()

    def _init_seq(self):
        """初始化章节顺序。"""
        ques_str = [f"ques{i}" for i in range(1, self.ques_count + 1)]
        self.seq = [
            "firstPage",           # 标题、摘要、关键词
            "RepeatQues",          # 一、问题重述
            "analysisQues",        # 二、问题分析
            "modelAssumption",     # 三、模型假设
            "symbol",              # 四、符号说明和数据预处理
            "eda",                 # 四、数据预处理（EDA部分）
            *ques_str,             # 五、模型的建立与求解
            "sensitivity_analysis", # 六、敏感性分析
            "judge",               # 七、模型的评价、改进与推广
        ]

    def set_res(self, key: str, writer_response: WriterResponse):
        """设置指定章节的写作结果。"""
        self.res[key] = {
            "response_content": writer_response.response_content,
            "footnotes": writer_response.footnotes,
        }

    def get_res(self):
        """获取所有章节的写作结果。"""
        return self.res

    def to_dict(self) -> dict:
        """序列化为可持久化的字典（用于断点续传 checkpoint）。"""
        return {
            "ques_count": self.ques_count,
            "res": self.res,
            "footnotes": self.footnotes,
        }

    @classmethod
    def from_dict(cls, work_dir: str, data: dict) -> "UserOutput":
        """从字典恢复 UserOutput（用于断点续传）。"""
        obj = cls(work_dir=work_dir, ques_count=data.get("ques_count", 0))
        obj.res = data.get("res", {})
        obj.footnotes = data.get("footnotes", {})
        return obj

    def save_checkpoint(self, path: str) -> None:
        """将当前结果保存为 checkpoint 文件。"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)

    def get_model_build_solve(self) -> str:
        """获取模型求解结果的摘要字符串。"""
        return ",".join(
            f"{key}-{value}"
            for key, value in self.res.items()
            if key.startswith("ques") and key != "ques_count"
        )

    def replace_references_with_uuid(self, text: str) -> str:
        """将文本中的引用标记替换为 UUID。"""
        references = re.findall(r"\{\[\^(\d+)\]:\s*(.*?)\}", text, re.DOTALL)

        for ref_num, ref_content in references:
            ref_content = ref_content.strip().rstrip(".")
            existing_uuid = None
            for uuid_key, footnote_data in self.footnotes.items():
                if footnote_data["content"] == ref_content:
                    existing_uuid = uuid_key
                    break

            if existing_uuid:
                text = re.sub(
                    rf"\{{\[\^{ref_num}\]:.*?\}}",
                    f"[{existing_uuid}]",
                    text,
                    flags=re.DOTALL,
                )
            else:
                new_uuid = str(uuid.uuid4())
                self.footnotes[new_uuid] = {"content": ref_content}
                text = re.sub(
                    rf"\{{\[\^{ref_num}\]:.*?\}}",
                    f"[{new_uuid}]",
                    text,
                    flags=re.DOTALL,
                )

        return text

    def sort_text_with_footnotes(self, replace_res: dict) -> dict:
        """按章节顺序排列文本并将 UUID 替换为连续编号。"""
        sort_res = {}
        ref_index = 1

        for seq_key in self.seq:
            if seq_key not in replace_res:
                continue
            text = replace_res[seq_key]["response_content"]
            uuid_list = re.findall(r"\[([a-f0-9-]{36})\]", text)
            for uid in uuid_list:
                text = text.replace(f"[{uid}]", f"[^{ref_index}]")
                if self.footnotes[uid].get("number") is None:
                    self.footnotes[uid]["number"] = ref_index
                ref_index += 1
            sort_res[seq_key] = {"response_content": text}

        return sort_res

    def append_footnotes_to_text(self, text: str) -> str:
        """在文本末尾追加参考文献列表。"""
        text += "\n\n## 参考文献"
        sorted_footnotes = sorted(
            self.footnotes.items(), key=lambda x: x[1].get("number", 0)
        )
        for _, footnote in sorted_footnotes:
            if "number" in footnote:
                text += f"\n\n[^{footnote['number']}]: {footnote['content']}"
        return text

    def get_result_to_save(self) -> str:
        """获取最终拼接的论文全文，包含引用处理和参考文献。"""
        replace_res = {}
        for key, value in self.res.items():
            new_text = self.replace_references_with_uuid(value["response_content"])
            replace_res[key] = {"response_content": new_text}

        sort_res = self.sort_text_with_footnotes(replace_res)

        full_res_1 = "\n\n".join(
            [sort_res[key]["response_content"] for key in self.seq if key in sort_res]
        )

        full_res = self.append_footnotes_to_text(full_res_1)
        return full_res

    def save_result(self):
        """将结果保存为 res.json 和 res.md 文件。"""
        with open(os.path.join(self.work_dir, "res.json"), "w", encoding="utf-8") as f:
            json.dump(self.res, f, ensure_ascii=False, indent=4)

        res_path = os.path.join(self.work_dir, "res.md")
        with open(res_path, "w", encoding="utf-8") as f:
            f.write(self.get_result_to_save())
