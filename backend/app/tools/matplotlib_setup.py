"""Matplotlib 初始化配置模块，为代码沙盒注入中文字体和学术绘图样式。"""

import os
import platform


def build_matplotlib_init_code(work_dir: str) -> str:
    """构建 Matplotlib 初始化代码。

    Args:
        work_dir: 工作目录路径。

    Returns:
        初始化代码字符串。
    """
    system = platform.system()

    # 中文字体候选列表
    if system == "Windows":
        font_candidates = [
            "Microsoft YaHei",
            "SimHei",
            "SimSun",
            "KaiTi",
            "FangSong",
        ]
    elif system == "Darwin":
        font_candidates = [
            "PingFang SC",
            "Hiragino Sans GB",
            "STHeiti",
            "Songti SC",
        ]
    else:
        font_candidates = [
            "Noto Sans CJK SC",
            "WenQuanYi Micro Hei",
            "Droid Sans Fallback",
        ]

    code = f"""
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# 工作目录
os.chdir(r"{work_dir}")

# 中文字体检测
font_candidates = {font_candidates}
CJK_FONT = None
for font_name in font_candidates:
    try:
        font_path = fm.findfont(font_name, fallback_to_default=False)
        if font_path:
            CJK_FONT = font_name
            print(f"[matplotlib_setup] 中文字体已加载: {{font_name}}")
            break
    except Exception:
        continue

if CJK_FONT is None:
    print("[matplotlib_setup] 未找到中文字体，可能显示方框")
    CJK_FONT = "sans-serif"

# 学术绘图配色方案
COLORS = {{
    'primary': '#2563EB',      # 蓝色
    'secondary': '#10B981',    # 绿色
    'accent': '#F59E0B',       # 橙色
    'danger': '#EF4444',       # 红色
    'purple': '#8B5CF6',       # 紫色
    'pink': '#EC4899',         # 粉色
    'gray': '#6B7280',         # 灰色
    'light_gray': '#E5E7EB',   # 浅灰
}}

DEFAULT_COLORS = list(COLORS.values())

# 图表尺寸（英寸）
FIG_SINGLE = (6, 4)       # 单栏图
FIG_DOUBLE = (10, 4)      # 双栏图
FIG_WIDE = (12, 5)        # 宽图
FIG_SQUARE = (6, 6)       # 方形图

# Matplotlib 全局样式设置
plt.rcParams.update({{
    'font.family': 'sans-serif',
    'font.sans-serif': [CJK_FONT] + font_candidates + ['DejaVu Sans'],
    'axes.unicode_minus': False,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
    'legend.frameon': False,
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14,
}})

print("[matplotlib_setup] Matplotlib 初始化完成")
"""
    return code
