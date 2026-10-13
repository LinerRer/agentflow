import uuid
from langgraph.graph import StateGraph, END
from core.state import AgentFlowState
from core.executor import node_executor, init_task_state
from core.trace import trace_manager
from core.replay import replay_player
from core.debugger import task_debugger


# ===================== 复用测试节点 =====================
@node_executor("input_process")
def input_process_node(state: AgentFlowState) -> AgentFlowState:
    user_input = state["user_input"]
    processed = f"[已处理] {user_input.upper()}"
    state["task_plan"] = "输入处理完成"
    state["data_result"] = processed
    state["current_node"] = "input_process"
    return state


@node_executor("output_generate")
def output_generate_node(state: AgentFlowState) -> AgentFlowState:
    result = f"最终输出：{state['data_result']}，处理完成"
    state["output_content"] = result
    state["current_node"] = "output_generate"
    state["status"] = "completed"
    return state


def build_test_workflow():
    workflow = StateGraph(AgentFlowState)
    workflow.add_node("input_process", input_process_node)
    workflow.add_node("output_generate", output_generate_node)
    workflow.set_entry_point("input_process")
    workflow.add_edge("input_process", "output_generate")
    workflow.add_edge("output_generate", END)
    return workflow.compile()


# ===================== 1. 测试全链路追踪 =====================
def test_trace(task_id, trace_id):
    print("\n" + "=" * 60)
    print("  测试1：全链路追踪管理器")
    print("=" * 60)

    # 按任务ID查询
    task_trace = trace_manager.get_task_trace(task_id)
    print(f"✅ 按任务ID查询成功")
    print(f"  任务名称：{task_trace['task']['task_name']}")
    print(f"  任务状态：{task_trace['task']['status']}")
    print(f"  日志条数：{len(task_trace['logs'])}")
    print(f"  快照条数：{len(task_trace['snapshots'])}")
    print(f"  异常条数：{len(task_trace['exceptions'])}")

    # 按trace_id全链路查询
    full_trace = trace_manager.get_full_trace(trace_id)
    print(f"\n✅ 按trace_id全链路查询成功")
    print(f"  关联任务数：{full_trace['task_count']}")
    print(f"  总日志条数：{full_trace['log_count']}")
    print(f"  总快照条数：{full_trace['snapshot_count']}")

    # 关键词搜索
    search_result = trace_manager.search_by_keyword("执行完成")
    print(f"\n✅ 关键词搜索成功，匹配到 {len(search_result)} 条日志")


# ===================== 2. 测试执行回放器 =====================
def test_replay(task_id):
    print("\n" + "=" * 60)
    print("  测试2：执行回放器")
    print("=" * 60)

    # 加载任务
    replay_player.load_task(task_id)

    # 全量回放
    all_steps = replay_player.play_all()
    print(f"✅ 全量回放完成，共 {len(all_steps)} 个节点步骤")

    for step in all_steps:
        print(f"\n  步骤 {step['step']}：{step['node_name']}")
        print(f"    状态：{step['status']}")
        print(f"    耗时：{step['duration']} 秒")
        print(f"    执行前数据：{step['before_state'].get('data_result', '空')}")
        print(f"    执行后数据：{step['after_state'].get('data_result', '空')}")

    # 单步步进回放
    replay_player.reset()
    print("\n✅ 单步步进回放测试：")
    step1 = replay_player.step_forward()
    print(f"  第1步：{step1['node_name']} - {step1['start_log']}")
    step2 = replay_player.step_forward()
    print(f"  第2步：{step2['node_name']} - {step2['end_log']}")
    step3 = replay_player.step_forward()
    print(f"  结束：{step3['message']}")


# ===================== 3. 测试单步调试器 =====================
def test_debugger():
    print("\n" + "=" * 60)
    print("  测试3：单步调试器")
    print("=" * 60)

    # 初始化测试任务
    task_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    initial_state = init_task_state(
        task_id=task_id,
        task_name="调试测试任务",
        task_type="debug_test",
        user_input="debug test input",
        trace_id=trace_id
    )

    # 构建工作流
    app = build_test_workflow()

    # 加载调试器
    task_debugger.load(app, initial_state)

    # 第一步
    step1 = task_debugger.step_next()
    print(f"✅ 第1步执行：{step1['node_name']}")
    print(f"  当前data_result：{step1['state']['data_result']}")

    # 中途修改状态
    task_debugger.modify_state("data_result", "[已修改] DEBUG TEST INPUT")
    print(f"  修改后data_result：{task_debugger.get_state()['data_result']}")

    # 第二步
    step2 = task_debugger.step_next()
    print(f"\n✅ 第2步执行：{step2['node_name']}")
    print(f"  最终输出：{step2['state']['output_content']}")

    # 结束
    step3 = task_debugger.step_next()
    print(f"\n✅ {step3['message']}")
    print(f"  总执行步数：{step3['step']}")


# ===================== 主测试入口 =====================
if __name__ == "__main__":
    print("\n🚀 阶段三：观测体系功能测试开始")

    # 先运行一个任务生成测试数据
    task_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    initial_state = init_task_state(
        task_id=task_id,
        task_name="阶段三测试任务",
        task_type="test",
        user_input="hello phase3 test",
        trace_id=trace_id
    )
    app = build_test_workflow()
    app.invoke(initial_state)
    print(f"✅ 测试任务运行完成，task_id：{task_id}")

    # 1. 测试全链路追踪
    test_trace(task_id, trace_id)

    # 2. 测试执行回放
    test_replay(task_id)

    # 3. 测试单步调试
    test_debugger()

    print("\n" + "=" * 60)
    print("🎉 阶段三所有功能测试通过！")
    print("=" * 60)
