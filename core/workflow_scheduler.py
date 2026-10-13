from langgraph.graph import StateGraph, END
from core.state import AgentFlowState
from core.event_bus import event_bus, Event, EVENT_NODE_COMPLETE, EVENT_TASK_COMPLETE


class WorkflowScheduler:
    """
    基于事件的工作流调度器
    通过事件订阅来配置节点流转关系，替代硬编码边
    """

    def __init__(self):
        self.nodes = {}  # 注册的节点：{节点名: 节点函数}
        self.routes = {}  # 路由规则：{源节点名: 目标节点名}
        self.entry_point = None  # 入口节点

    def register_node(self, node_name: str, node_func):
        """注册节点"""
        self.nodes[node_name] = node_func

    def set_entry(self, node_name: str):
        """设置入口节点"""
        self.entry_point = node_name

    def add_route(self, from_node: str, to_node: str):
        """
        添加路由规则：from_node 完成后，执行 to_node
        替代原来的 add_edge
        """
        self.routes[from_node] = to_node

        # 订阅节点完成事件，触发下一个节点
        def on_node_complete(event: Event):
            if event.source == from_node:
                # 事件源匹配，触发目标节点
                pass  # 具体执行由LangGraph状态机驱动，这里只做路由配置

        event_bus.subscribe(EVENT_NODE_COMPLETE, on_node_complete)

    def build(self) -> StateGraph:
        """
        构建LangGraph状态机
        根据注册的节点和路由规则自动生成边
        """
        if not self.entry_point:
            raise Exception("未设置入口节点")

        workflow = StateGraph(AgentFlowState)

        # 1. 注册所有节点
        for name, func in self.nodes.items():
            workflow.add_node(name, func)

        # 2. 设置入口
        workflow.set_entry_point(self.entry_point)

        # 3. 根据路由规则添加边
        for from_node, to_node in self.routes.items():
            if to_node == "END":
                workflow.add_edge(from_node, END)
            else:
                workflow.add_edge(from_node, to_node)

        # 4. 编译
        return workflow.compile()


# 全局调度器实例
scheduler = WorkflowScheduler()
