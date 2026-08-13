# MMmaker

> 国奖级数学建模竞赛自动化系统

MMmaker 是一套完整的数学建模竞赛自动化解决方案，通过多智能体协作完成从问题分析、数学建模、代码实现到论文撰写的全流程，目标是生成达到国奖水平的竞赛论文。

## 核心特性

- **多智能体协作**：协调者、建模手、代码手、写作手、评审手五大角色分工协作
- **完整工作流**：问题拆解 → 建模设计 → 代码实现 → 论文撰写 → 质量评审 → 反馈优化
- **国奖级标准**：内置建模规范、写作规范、评审标准，确保输出质量
- **人机协作(HIL)**：关键节点暂停等待用户审批，支持 6 种决策动作
- **质量反馈循环**：评审手评分 → 反馈注入 → 重跑优化
- **代码沙盒**：本地 Jupyter / E2B 云端双模式执行
- **文献检索**：OpenAlex 学术搜索，自动生成引用
- **可视化规范**：学术论文级图表生成，符合竞赛评审标准

## 项目结构

```
MMmaker/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── core/           # 核心逻辑
│   │   │   ├── agents/     # 智能体实现
│   │   │   ├── llm/        # LLM 调用层
│   │   │   ├── prompts/    # 提示词模板
│   │   │   ├── workflow.py # 工作流编排
│   │   │   └── flows.py    # 流程定义
│   │   ├── routers/        # API 路由
│   │   ├── schemas/        # 数据模型
│   │   ├── services/       # 基础设施服务
│   │   ├── tools/          # 工具（代码解释器、文献检索等）
│   │   └── utils/          # 工具函数
│   └── pyproject.toml
├── frontend/               # 前端界面
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── pages/          # 页面
│   │   ├── stores/         # 状态管理
│   │   └── utils/          # 工具函数
│   └── package.json
├── docs/                   # 文档
├── docker-compose.yml      # Docker 编排
└── README.md
```

## 快速开始

### Docker 部署（推荐）

```bash
docker-compose up -d
```

访问：
- 前端界面：http://localhost:5173
- 后端 API：http://localhost:8000

### 本地部署

**后端**：
```bash
cd backend
uv sync
ENV=DEV uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端**：
```bash
cd frontend
pnpm i
pnpm run dev
```

## 智能体角色

| 角色 | 职责 | 关键能力 |
|------|------|---------|
| CoordinatorAgent | 问题拆解 | 识别建模问题、拆解子问题、结构化输出 |
| ModelerAgent | 建模设计 | 模型选择、方案设计、可视化策略 |
| CoderAgent | 代码实现 | 代码生成、沙盒执行、错误反思 |
| WriterAgent | 论文撰写 | 学术写作、文献引用、图表插入 |
| ReviewerAgent | 质量评审 | 评分反馈、改进建议、重跑决策 |

## 工作流

```
用户输入题目
    ↓
CoordinatorAgent 拆解问题
    ↓
ModelerAgent 设计建模方案
    ↓
[HIL 检查点：模型选择确认]
    ↓
循环执行：
  ├── CoderAgent 生成并执行代码
  ├── WriterAgent 撰写对应章节
  └── ReviewerAgent 评审反馈
    ↓
[HIL 检查点：论文评审]
    ↓
生成最终论文
```

## 国奖级质量标准

### 建模规范
- 模型选择决策树（预测/评价/分类/优化/统计/仿真）
- 物理可行性约束检查
- 参数定量依据（数据统计/文献引用/校准实验）
- 敏感性分析必须覆盖关键参数

### 写作规范
- 段落式写作，禁止分点列表
- 每张图片配 3 行以上分析
- 模型选择必须对比备选方案
- 因果与相关严格区分

### 评审标准
- 摘要质量（1页内完整概述）
- 模型合理性（假设有依据、参数有来源）
- 结果可信度（误差分析、交叉验证）
- 论文完整性（结构完整、逻辑清晰）

## 配置说明

每个智能体可独立配置不同的 LLM：

```env
COORDINATOR_API_KEY=your_key
COORDINATOR_MODEL=gpt-4o
MODELER_API_KEY=your_key
MODELER_MODEL=gpt-4o
CODER_API_KEY=your_key
CODER_MODEL=gpt-4o
WRITER_API_KEY=your_key
WRITER_MODEL=gpt-4o
REVIEWER_API_KEY=your_key
REVIEWER_MODEL=gpt-4o
```

## 许可证

MIT License
