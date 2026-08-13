"""命令行工具模块，提供 ASCII 横幅和 CLI 输出。"""


def get_ascii_banner() -> str:
    """返回 MMmaker ASCII 横幅。"""
    return r"""
 __  __ __  __
|  \/  |  \/  |  _ __ ___   __ _  __ _  ___ _ __
| |\/| | |\/| | | '_ ` _ \ / _` |/ _` |/ _ \ '__|
| |  | | |  | | | | | | | | (_| | (_| |  __/ |
|_|  |_|_|  |_| |_| |_| |_|\__,_|\__, |\___|_|
                                 |___/

        MMmaker - 国奖级数学建模竞赛自动化系统
"""


def center_cli_str(text: str, width: int = 60) -> str:
    """居中显示文本。"""
    return text.center(width)
