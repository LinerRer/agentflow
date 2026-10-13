import uuid
from typing import List, Dict, Any
from core.executor import init_task_state
from core.state import AgentFlowState
from storage.dao import task_dao
from core.event_bus import event_bus, Event, EVENT_TASK_COMPLETE


class SubtaskManager:
    """
    子任务管理器
    负责子任务的创建、执行、状态隔离与结果聚合
    """

    def create_subtask(self, parent_state: AgentFlowState, subtask_name: str, subtask_type: str,
                       user_input: str) -> dict:
        """
        创建子任务
        继承父任务的 trace_id，生成独立的 task_id
        """
        subtask_id = str(uuid.uuid4())
        trace_id = parent_state["trace_id"]  # 共享全链路追踪ID

        # 初始化子任务状态（同时创建数据库记录）
        subtask_state = init_task_state(
            task_id=subtask_id,
            task_name=subtask_name,
            task_type=subtask_type,
            user_input=user_input,
            trace_id=trace_id
        )

        # 标记父任务ID，用于关联查询
        subtask_state["context"]["parent_task_id"] = parent_state["task_id"]

        return subtask_state

    def execute_subtask(self, subtask_state: dict, workflow_app) -> dict:
        """
        执行单个子任务
        返回子任务最终状态
        """
        task_id = subtask_state["task_id"]

        try:
            # 更新子任务状态为运行中
            task_dao.update_task_status(task_id, "running")

            # 执行子任务工作流
            result_state = workflow_app.invoke(subtask_state)

            # 更新子任务状态为完成
            task_dao.update_task_status(task_id, "completed")

            # 发布子任务完成事件
            event_bus.publish(Event(
                event_type=EVENT_TASK_COMPLETE,
                source=task_id,
                data={"status": "completed"}
            ))

            return result_state

        except Exception as e:
            # 子任务失败，标记状态，不抛出异常，不中断父任务
            task_dao.update_task_status(task_id, "failed")
            subtask_state["status"] = "failed"
            subtask_state["message"] = f"子任务执行失败：{str(e)}"
            return subtask_state

    def execute_subtasks_serial(self, parent_state: dict, subtask_configs: List[Dict[str, Any]], workflow_builder) -> \
    List[dict]:
        """
        串行执行多个子任务
        subtask_configs: [{"name": "", "type": "", "input": "", "workflow": 工作流构建函数}]
        """
        results = []
        for config in subtask_configs:
            # 创建子任务
            subtask_state = self.create_subtask(
                parent_state=parent_state,
                subtask_name=config["name"],
                subtask_type=config["type"],
                user_input=config["input"]
            )

            # 构建子任务工作流
            workflow_app = config["workflow_builder"]()

            # 执行子任务
            result = self.execute_subtask(subtask_state, workflow_app)
            results.append(result)

        return results

    def aggregate_results(self, parent_state: dict, subtask_results: List[dict],
                          result_key: str = "subtask_results") -> dict:
        """
        把子任务结果聚合到父任务状态中
        """
        aggregated = []
        for res in subtask_results:
            aggregated.append({
                "task_id": res["task_id"],
                "task_name": res["task_name"],
                "status": res["status"],
                "output": res.get("output_content", ""),
                "message": res.get("message", "")
            })

        parent_state["context"][result_key] = aggregated
        return parent_state


# 全局子任务管理器实例
subtask_manager = SubtaskManager()
