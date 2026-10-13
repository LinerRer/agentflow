# 🤖 AgentFlow 智能工作流平台

> 基于 LangGraph 的可观测、可回溯、可调试智能 Agent 平台

---

## ✨ 项目特性

- **工作流编排**：基于 LangGraph 状态机，支持多节点线性工作流
- **全链路追踪**：每一步自动记录日志，基于 trace_id 聚合完整执行时间线
- **状态快照**：节点执行前后自动保存状态，支持版本管理和按版本恢复
- **执行回放**：离线回放历史任务，支持单步前进和状态前后对比
- **单步调试**：逐节点执行，可查看和修改中间状态
- **异常分级治理**：轻微异常自动重试（指数退避），一般异常降级跳过，严重异常终止
- **事件总线**：发布-订阅模式，支持生命周期事件监听和功能扩展
- **子任务管理**：支持子任务创建、串行执行、状态隔离与结果聚合
- **可视化界面**：Streamlit 搭建的 Web 界面，操作简单直观

---

## 🛠 技术栈

| 分类 | 技术 |
|------|------|
| 语言 | Python 3.11 |
| 工作流引擎 | LangGraph |
| 大模型框架 | LangChain |
| 大模型 | Ollama + Qwen2:7B（本地部署） |
| Web 框架 | Streamlit |
| 数据库 | SQLite |

---

## 📁 项目结构

```
agentflow/
├── app.py                          # Streamlit 前端入口
├── 启动平台.bat                     # Windows 一键启动脚本
├── requirements.txt                # Python 依赖
├── .streamlit/
│   └── config.toml                 # 主题配置
├── docs/
│   └── 需求分析与技术栈.md          # 详细需求与技术文档
├── tests/
│   └── test_core.py                # 单元测试
├── agents/
│   └── data_analysis_agent.py     # 数据分析业务 Agent（3个节点）
├── config/
│   └── settings.py                 # 全局配置参数
├── core/
│   ├── executor.py                 # 节点执行器（装饰器，统一日志/快照/重试）
│   ├── state.py                    # 统一状态模型（TypedDict）
│   ├── snapshot.py                 # 状态快照管理器
│   ├── trace.py                    # 全链路追踪管理器
│   ├── replay.py                   # 执行回放器
│   ├── debugger.py                 # 单步调试器
│   ├── exception_handler.py        # 异常分级处理器
│   ├── event_bus.py                # 事件总线（发布-订阅）
│   ├── subtask.py                  # 子任务管理器
│   └── workflow_scheduler.py       # 基于事件的工作流调度器
└── storage/
    ├── models.py                   # 数据库建表 SQL
    ├── dao.py                      # 数据访问对象（DAO）
    └── agentflow.db                # SQLite 数据库文件
```

---

## 🚀 快速开始

### 前置条件

1. Python 3.10+
2. 已安装 Ollama 并拉取 qwen2:7b 模型
   ```bash
   ollama pull qwen2:7b
   ```

### 安装依赖

```bash
cd agentflow
pip install -r requirements.txt
```

### 启动方式

**方式一：一键启动（Windows）**

双击 `启动平台.bat`，自动启动服务并打开浏览器。

**方式二：命令行启动**

```bash
streamlit run app.py
```

启动后浏览器自动打开 `http://localhost:8503`。

---

## 📖 使用说明

### 1. 新建任务

- 在「新建任务」页面输入数据分析需求
- 点击「提交任务」，系统自动执行三个节点：需求解析 → 数据分析 → 报告生成
- 执行完成后展示分析报告和任务ID、追踪ID

### 2. 任务列表

- 查看所有历史任务
- 支持按状态筛选（pending/running/completed/failed）
- 展开任务详情，可复制任务ID、追踪ID，查看详细日志

### 3. 全链路追踪

- 输入 Trace ID 查询完整执行链路
- 展示关联任务数、日志总数、快照总数、异常总数
- 以时间线形式展示所有执行日志
- 异常记录可展开查看完整错误堆栈

### 4. 执行回放

- 输入任务ID加载历史执行记录
- 通过滑块选择回放步骤
- 展示当前节点的名称、执行状态、耗时
- 对比节点执行前后的状态变化
- 展示该步骤的开始和结束日志

---

## 🧪 运行测试

```bash
python -m pytest tests/test_core.py -v
```

测试覆盖：状态模型、事件总线、异常分级处理器、快照管理器、DAO层、执行器装饰器等核心模块。

---

## 🏗 核心设计

### 节点执行器（装饰器模式）

所有业务节点通过 `@node_executor("节点名")` 装饰，自动获得：
- 执行前后自动写日志
- 执行前后自动存状态快照
- 异常自动重试（可配置次数）
- 重试耗尽后降级跳过
- 自动更新任务状态

业务代码零侵入，只需要关注业务逻辑本身。

### 异常分级策略

| 级别 | 判定条件 | 处理策略 |
|------|----------|----------|
| 轻微 minor | 超时、连接失败、网络错误、限流 | 指数退避自动重试，最多3次 |
| 一般 general | 参数错误、格式错误、字段缺失 | 跳过当前节点，继续后续流程 |
| 严重 severe | 核心配置丢失、数据损坏 | 终止任务，等待人工介入 |

### 数据库四表设计

- **tasks**：任务元信息（1条）
- **execution_logs**：执行日志（N条，一对多）
- **snapshots**：状态快照（N条，一对多）
- **exceptions**：异常记录（N条，一对多）

通过 task_id 和 trace_id 关联，形成完整的可观测数据体系。

---

## 📄 许可证

MIT License
