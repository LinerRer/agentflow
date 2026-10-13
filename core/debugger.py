from typing import Generator, Dict, Any
from core.state import AgentFlowState


class TaskDebugger:
    """
    任务单步调试器
    支持逐节点控制执行，每执行完一个节点暂停，可查看、修改状态后继续
    """

    def __init__(self):
        self.workflow_app = None  # 编译后的工作流
        self.current_state = None  # 当前状态
        self.step_stream = None  # 执行流生成器
        self.current_node = None  # 当前执行到的节点
        self.finished = False  # 是否执行完毕
        self.step_count = 0  # 已执行步数

    def load(self, workflow_app, initial_state: AgentFlowState):
        """
        加载工作流和初始状态，准备调试
        """
        self.workflow_app = workflow_app
        self.current_state = initial_state
        self.step_stream = self.workflow_app.stream(initial_state)
        self.finished = False
        self.step_count = 0
        self.current_node = None
        print(f"✅ 调试任务加载完成，任务ID：{initial_state['task_id']}")

    def step_next(self) -> Dict[str, Any]:
        """
        执行下一步（下一个节点）
        返回当前节点信息和执行后的状态
        """
        if self.finished:
            return {
                "finished": True,
                "message": "任务已执行完毕",
                "state": self.current_state
            }

        try:
            # 取下一个节点的执行结果（stream返回格式：{节点名: 状态}）
            chunk = next(self.step_stream)
            node_name = list(chunk.keys())[0]
            state = chunk[node_name]

            self.current_node = node_name
            self.current_state = state
            self.step_count += 1

            return {
                "finished": False,
                "step": self.step_count,
                "node_name": node_name,
                "state": state,
                "message": f"节点 [{node_name}] 执行完成"
            }

        except StopIteration:
            # 所有节点执行完毕
            self.finished = True
            return {
                "finished": True,
                "step": self.step_count,
                "state": self.current_state,
                "message": "所有节点执行完毕，任务完成"
            }

    def get_state(self) -> dict:
        """获取当前状态"""
        return self.current_state

    def modify_state(self, key: str, value: Any):
        """
        修改当前状态，修改后下一步将基于新状态执行
        注意：只能修改业务字段，不建议修改task_id、trace_id等基础字段
        """
        if self.current_state:
            self.current_state[key] = value
            print(f"✅ 状态字段 [{key}] 已修改")

    def run_all(self) -> dict:
        """一次性执行完剩余所有步骤"""
        while not self.finished:
            self.step_next()
        return self.current_state


# 全局调试器实例
task_debugger = TaskDebugger()
