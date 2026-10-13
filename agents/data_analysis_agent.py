from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from core.state import AgentFlowState
from core.executor import node_executor
from config.settings import LLM_MODEL_NAME, LLM_TEMPERATURE, LLM_TIMEOUT

# 初始化大模型
llm = ChatOllama(
    model=LLM_MODEL_NAME,
    temperature=LLM_TEMPERATURE,
    timeout=LLM_TIMEOUT
)


@node_executor("requirement_parse")
def requirement_parse_node(state: AgentFlowState) -> AgentFlowState:
    """节点1：需求解析 - 把用户输入拆解为分析任务计划"""
    user_input = state["user_input"]

    prompt = f"""
    请分析用户的数据分析需求，输出清晰的执行计划。
    用户需求：{user_input}

    请按以下格式输出：
    1. 需求核心目标
    2. 分析步骤
    3. 预期输出形式
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    state["task_plan"] = response.content
    state["current_node"] = "requirement_parse"
    return state


@node_executor("data_analysis")
def data_analysis_node(state: AgentFlowState) -> AgentFlowState:
    """节点2：数据分析 - 根据需求执行分析推理"""
    task_plan = state["task_plan"]
    user_input = state["user_input"]

    prompt = f"""
    根据以下需求和执行计划，进行详细的数据分析推理。
    用户需求：{user_input}
    执行计划：{task_plan}

    请输出详细的分析过程和结论。
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    state["analysis_result"] = response.content
    state["current_node"] = "data_analysis"
    return state


@node_executor("report_generate")
def report_generate_node(state: AgentFlowState) -> AgentFlowState:
    """节点3：报告生成 - 输出最终的结构化分析报告"""
    analysis_result = state["analysis_result"]
    user_input = state["user_input"]

    prompt = f"""
    基于以下分析结果，生成一份结构清晰的最终分析报告。
    用户原始需求：{user_input}
    分析结果：{analysis_result}

    要求：
    - 标题清晰
    - 分点阐述结论
    - 给出建议
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    state["output_content"] = response.content
    state["current_node"] = "report_generate"
    state["status"] = "completed"
    return state


def build_analysis_workflow():
    """构建完整的数据分析工作流"""
    from langgraph.graph import StateGraph, END

    workflow = StateGraph(AgentFlowState)

    # 注册节点
    workflow.add_node("requirement_parse", requirement_parse_node)
    workflow.add_node("data_analysis", data_analysis_node)
    workflow.add_node("report_generate", report_generate_node)

    # 设置入口
    workflow.set_entry_point("requirement_parse")

    # 连接边
    workflow.add_edge("requirement_parse", "data_analysis")
    workflow.add_edge("data_analysis", "report_generate")
    workflow.add_edge("report_generate", END)

    return workflow.compile()
