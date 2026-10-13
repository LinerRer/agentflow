import uuid
from langgraph.graph import StateGraph, END
from core.state import AgentFlowState
from core.executor import node_executor, init_task_state
from storage.dao import task_dao, log_dao, snapshot_dao


# ===================== 1. 定义测试节点（使用执行器装饰器） =====================
@node_executor("input_process")
def input_process_node(state: AgentFlowState) -> AgentFlowState:
    """测试节点1：处理用户输入"""
    user_input = state["user_input"]
    processed = f"[已处理] {user_input.upper()}"

    # 更新状态
    state["task_plan"] = "输入处理完成"
    state["data_result"] = processed
    state["current_node"] = "input_process"
    return state


@node_executor("output_generate")
def output_generate_node(state: AgentFlowState) -> AgentFlowState:
    """测试节点2：生成最终结果"""
    result = f"最终输出：{state['data_result']}，处理完成"

    state["output_content"] = result
    state["current_node"] = "output_generate"
    state["status"] = "completed"
    return state


# ===================== 2. 构建状态机工作流 =====================
def build_test_workflow():
    """构建最简测试工作流"""
    workflow = StateGraph(AgentFlowState)

    # 添加节点
    workflow.add_node("input_process", input_process_node)
    workflow.add_node("output_generate", output_generate_node)

    # 设置入口
    workflow.set_entry_point("input_process")

    # 连接边
    workflow.add_edge("input_process", "output_generate")
    workflow.add_edge("output_generate", END)

    # 编译
    return workflow.compile()


# ===================== 3. 运行测试 =====================
def run_test():
    print("=" * 50)
    print("  AgentFlow 核心底座验证测试")
    print("=" * 50)

    # 生成唯一ID
    task_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    user_input = "hello agentflow test"

    # 1. 初始化任务状态（同时创建数据库任务记录）
    initial_state = init_task_state(
        task_id=task_id,
        task_name="基础功能测试任务",
        task_type="test",
        user_input=user_input,
        trace_id=trace_id
    )
    print(f"✅ 任务创建成功，任务ID：{task_id}")

    # 2. 构建工作流
    app = build_test_workflow()
    print("✅ 工作流构建完成")

    # 3. 执行工作流
    print("\n🚀 开始执行工作流...\n")
    result_state = app.invoke(initial_state)

    # 4. 输出结果
    print("\n" + "=" * 50)
    print("✅ 工作流执行完成")
    print(f"任务状态：{result_state['status']}")
    print(f"最终输出：{result_state['output_content']}")
    print("=" * 50)

    # 5. 验证数据库数据
    print("\n📊 数据库验证：")
    # 查询任务
    task = task_dao.get_task(task_id)
    print(f"  任务记录：存在，状态={task['status']}")

    # 查询日志
    logs = log_dao.get_task_logs(task_id)
    print(f"  执行日志：{len(logs)} 条")

    # 查询快照
    snapshots = snapshot_dao._query_all(
        "SELECT * FROM snapshots WHERE task_id = ?", (task_id,)
    )
    print(f"  状态快照：{len(snapshots)} 个")
    print("\n🎉 阶段一核心底座验证通过！")


if __name__ == "__main__":
    run_test()
