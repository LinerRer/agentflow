from typing import TypedDict, Optional, Dict, Any
from datetime import datetime


class AgentFlowState(TypedDict):
    """
    全局工作流状态模型
    所有节点的输入输出都必须遵循此结构
    """
    # ========== 任务基础信息 ==========
    task_id: str  # 任务唯一ID
    task_name: str  # 任务名称
    task_type: str  # 任务类型
    trace_id: str  # 全链路追踪ID

    # ========== 执行控制信息 ==========
    current_node: str  # 当前执行节点
    status: str  # 任务状态：pending/running/paused/failed/completed
    iteration: int  # 当前迭代次数
    error_count: int  # 错误计数

    # ========== 业务上下文数据 ==========
    user_input: str  # 用户原始输入
    task_plan: str  # 任务拆解计划
    data_result: str  # 数据处理结果
    analysis_result: str  # 分析结论
    output_content: str  # 最终输出内容

    # ========== 扩展字段 ==========
    context: Dict[str, Any]  # 通用扩展上下文，存放自定义数据
    message: Optional[str]  # 临时消息
