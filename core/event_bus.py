import uuid
from datetime import datetime
from typing import Dict, List, Callable, Any


class Event:
    """事件模型"""

    def __init__(self, event_type: str, source: str, data: dict = None):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type  # 事件类型
        self.source = source  # 发布源（节点名）
        self.data = data or {}  # 事件载荷
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class EventBus:
    """
    事件总线
    发布-订阅模式，支持事件注册、发布、订阅
    """

    def __init__(self):
        # 事件订阅表：{事件类型: [订阅回调函数列表]}
        self.subscribers: Dict[str, List[Callable[[Event], Any]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[Event], Any]):
        """
        订阅事件
        :param event_type: 事件类型
        :param callback: 回调函数，接收Event对象
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Event], Any]):
        """取消订阅"""
        if event_type in self.subscribers:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)

    def publish(self, event: Event):
        """
        发布事件
        同步调用所有订阅该事件的回调函数
        """
        if event.event_type not in self.subscribers:
            return

        for callback in self.subscribers[event.event_type]:
            try:
                callback(event)
            except Exception as e:
                # 订阅者异常不影响事件总线
                print(f"[事件总线] 订阅者执行异常: {str(e)}")


# ===================== 标准事件类型定义 =====================
# 节点生命周期事件
EVENT_NODE_START = "node.start"  # 节点开始执行
EVENT_NODE_COMPLETE = "node.complete"  # 节点执行完成
EVENT_NODE_FAILED = "node.failed"  # 节点执行失败
EVENT_NODE_SKIP = "node.skip"  # 节点跳过

# 任务生命周期事件
EVENT_TASK_CREATE = "task.create"  # 任务创建
EVENT_TASK_START = "task.start"  # 任务开始
EVENT_TASK_COMPLETE = "task.complete"  # 任务完成
EVENT_TASK_FAILED = "task.failed"  # 任务失败

# 全局事件总线实例
event_bus = EventBus()
