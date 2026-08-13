"""共享的提示词工具函数。"""


def get_reflection_prompt(error_message: str, code: str) -> str:
    """生成代码错误反思提示词。

    Args:
        error_message: 错误信息。
        code: 出错的代码。

    Returns:
        反思提示词字符串。
    """
    return f"""The code execution encountered an error:
{error_message}

Please analyze the error, identify the cause, and provide a corrected version of the code.
Consider:
1. Syntax errors
2. Missing imports
3. Incorrect variable names or types
4. File path issues
5. Any other potential issues
6. If a task repeatedly fails to complete, try breaking down the code, changing your approach, or simplifying the model.
7. Don't ask user anything about how to do and next to do, just do it by yourself.

Previous code:
{code}

Please provide an explanation of what went wrong and remember to call the function tools to retry.
"""


def get_completion_check_prompt(prompt: str, text_to_gpt: str) -> str:
    """生成任务完成检查提示词。

    Args:
        prompt: 原始任务描述。
        text_to_gpt: 最新执行结果。

    Returns:
        完成检查提示词字符串。
    """
    return f"""
Please analyze the current state and determine if the task is fully completed:

Original task: {prompt}

Latest execution results:
{text_to_gpt}

Consider:
1. Have all required data processing steps been completed?
2. Have all necessary files been saved?
3. Are there any remaining steps needed?
4. Is the output satisfactory and complete?
5. If a task repeatedly fails to complete, try switching paths, simplifying paths, or skipping directly. Don't fall into repeated retries.
6. Try to complete the task in fewer dialogue turns.
7. If the task is complete, please provide a short summary of what was accomplished and don't call function tool.
8. If the task is not complete, please rethink how to do and call function tool.
9. Don't ask user anything about how to do and next to do, just do it by yourself.
10. Have a good visualization?
"""
