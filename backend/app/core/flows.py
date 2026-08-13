"""工作流程定义模块，管理建模任务的求解和写作流程。"""

from app.models.user_output import UserOutput
from app.schemas.A2A import ModelerToCoder
from app.tools.base_interpreter import BaseCodeInterpreter


class Flows:
    """管理数学建模任务的求解流程和写作流程。"""

    def __init__(self, questions: dict[str, str | int]):
        self.flows: dict[str, dict] = {}
        self.questions: dict[str, str | int] = questions

    def set_flows(self, ques_count: int):
        """根据问题数量设置流程节点。

        Args:
            ques_count: 问题数量。
        """
        ques_str = [f"ques{i}" for i in range(1, ques_count + 1)]
        seq = [
            "firstPage",
            "RepeatQues",
            "analysisQues",
            "modelAssumption",
            "symbol",
            "eda",
            *ques_str,
            "sensitivity_analysis",
            "judge",
        ]
        self.flows = {key: {} for key in seq}

    def get_solution_flows(
        self, questions: dict[str, str | int], modeler_response: ModelerToCoder
    ) -> dict[str, dict]:
        """生成求解阶段的流程配置。

        Args:
            questions: 包含各问题描述的字典。
            modeler_response: 建模手的响应，包含各问题的解决方案。

        Returns:
            求解流程配置字典，键为任务名，值包含 coder_prompt 等信息。
        """
        questions_quesx = {
            key: value
            for key, value in questions.items()
            if key.startswith("ques") and key != "ques_count"
        }
        solutions = modeler_response.questions_solution

        ques_flow = {
            key: {
                "coder_prompt": f"""
                        参考建模手给出的解决方案：{solutions.get(key, "")}
                        完成如下问题：{value}
                    """,
            }
            for key, value in questions_quesx.items()
        }

        flows = {
            "eda": {
                "coder_prompt": f"""
                        参考建模手给出的解决方案：{solutions.get("eda", "对数据进行探索性分析")}
                        对当前目录下数据进行EDA分析(数据清洗,可视化),清洗后的数据保存当前目录下,**不需要复杂的模型**
                    """,
            },
            **ques_flow,
            "sensitivity_analysis": {
                "coder_prompt": f"""
                        参考建模手给出的解决方案：{solutions.get("sensitivity_analysis", "对模型进行灵敏度分析")}
                        完成敏感性分析
                    """,
            },
        }
        return flows

    def get_write_flows(
        self, user_output: UserOutput, config_template: dict, bg_ques_all: str
    ) -> dict[str, str]:
        """生成写作阶段的流程配置。

        Args:
            user_output: 用户输出管理对象。
            config_template: 竞赛模板配置。
            bg_ques_all: 完整题目背景。

        Returns:
            写作流程配置字典，键为章节名，值为写作提示。
        """
        model_build_solve = user_output.get_model_build_solve()

        write_flows = {
            "firstPage": f"""
                根据以下信息撰写论文的标题、摘要和关键词：
                题目背景：{bg_ques_all}
                已完成的研究工作：{model_build_solve}
                要求：摘要必须包含问题概述、方法、结果（含具体数值）、结论，关键词4-5个。
            """,
            "RepeatQues": f"""
                根据以下信息撰写"一、问题重述"章节：
                题目背景：{bg_ques_all}
                要求：完整重述问题背景和各子问题，语言流畅，段落式写作。
            """,
            "analysisQues": f"""
                根据以下信息撰写"二、问题分析"章节：
                题目背景：{bg_ques_all}
                建模方案：{model_build_solve}
                要求：分析每个问题的类型、模型选择理由、求解思路。
            """,
            "modelAssumption": f"""
                根据以下信息撰写"三、模型假设"章节：
                建模方案：{model_build_solve}
                要求：列出所有假设，每个假设附合理性说明。
            """,
            "symbol": f"""
                根据以下信息撰写"四、符号说明与数据预处理"章节：
                建模方案：{model_build_solve}
                要求：列出所有符号及其含义，描述数据预处理过程。
            """,
            "judge": f"""
                根据以下信息撰写"七、模型的评价、改进与推广"章节：
                建模方案：{model_build_solve}
                要求：评价模型优点（多于缺点）、缺点（2-3个）、改进方向、推广价值。
            """,
        }
        return write_flows

    def get_writer_prompt(
        self,
        key: str,
        coder_response: str,
        code_interpreter: BaseCodeInterpreter,
        config_template: dict,
    ) -> str:
        """生成写作手的提示词。

        Args:
            key: 章节标识。
            coder_response: 代码执行结果。
            code_interpreter: 代码解释器。
            config_template: 竞赛模板配置。

        Returns:
            写作提示词。
        """
        code_output = code_interpreter.get_code_output(key)
        created_images = code_interpreter.get_created_images(key)

        prompt = f"""
请撰写"{key}"部分的论文内容。

## 代码执行结果
{coder_response}

## 代码输出
{code_output}

## 生成的图片
{chr(10).join(f"- {img}" for img in created_images) if created_images else "无"}

## 要求
1. 必须插入所有生成的图片
2. 每张图片配3行以上分析解读
3. 段落式写作，禁止分点列表
4. 包含具体数值和结果
5. 符合学术论文写作规范
"""
        return prompt
