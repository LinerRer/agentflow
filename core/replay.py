from core.trace import trace_manager


class ReplayPlayer:
    """
    任务执行回放器
    基于日志和快照，逐节点还原任务执行过程
    支持全量回放、单步步进、状态对比
    """

    def __init__(self):
        self.task_id = None
        self.trace_data = None
        self.step_index = 0
        self.node_steps = []

    def load_task(self, task_id: str):
        """加载要回放的任务，构建回放步骤"""
        self.task_id = task_id
        self.trace_data = trace_manager.get_task_trace(task_id)

        if "error" in self.trace_data:
            raise Exception(self.trace_data["error"])

        self._build_replay_steps()
        self.step_index = 0
        print(f"✅ 任务 {task_id} 加载完成，共 {len(self.node_steps)} 个回放步骤")

    def _build_replay_steps(self):
        """构建回放步骤：每个节点对应一个步骤，包含执行前/后状态"""
        logs = self.trace_data["logs"]
        snapshots = self.trace_data["snapshots"]

        # 按节点分组快照
        snapshot_map = {}
        for snap in snapshots:
            node = snap["node_name"]
            if node not in snapshot_map:
                snapshot_map[node] = {"before": None, "after": None}
            snapshot_map[node][snap["snapshot_type"]] = snap

        # 按节点开始日志构建步骤
        node_start_logs = [log for log in logs if log["log_type"] == "node_start"]
        node_end_logs = [log for log in logs if log["log_type"] in ("node_end", "node_skip")]
        end_log_map = {log["node_name"]: log for log in node_end_logs}

        self.node_steps = []
        for start_log in node_start_logs:
            node_name = start_log["node_name"]
            end_log = end_log_map.get(node_name)
            snap = snapshot_map.get(node_name, {})

            # 根据日志类型判断状态
            if end_log and end_log["log_type"] == "node_end":
                status = "completed"
                end_content = end_log["content"]
            elif end_log and end_log["log_type"] == "node_skip":
                status = "skipped"
                end_content = end_log["content"]
            else:
                status = "failed"
                end_content = "执行失败"

            step = {
                "node_name": node_name,
                "start_time": start_log["create_time"],
                "end_time": end_log["create_time"] if end_log else "",
                "duration": end_log["duration"] if end_log else 0,
                "status": status,
                "before_state": snap["before"]["state_data"] if snap.get("before") else {},
                "after_state": snap["after"]["state_data"] if snap.get("after") else {},
                "start_log": start_log["content"],
                "end_log": end_content
            }
            self.node_steps.append(step)

    def step_forward(self) -> dict:
        """单步向前回放，返回当前步骤详情"""
        if self.step_index >= len(self.node_steps):
            return {"finished": True, "message": "已回放至终点"}

        step = self.node_steps[self.step_index]
        self.step_index += 1
        return {
            "finished": False,
            "step": self.step_index,
            "total": len(self.node_steps),
            **step
        }

    def play_all(self) -> list:
        """一次性回放全部步骤，返回完整执行链路"""
        return [
            {"step": i + 1, **step}
            for i, step in enumerate(self.node_steps)
        ]

    def get_current_state(self) -> dict:
        """获取当前回放位置的最终状态"""
        if self.step_index == 0:
            return {}
        return self.node_steps[self.step_index - 1]["after_state"]

    def reset(self):
        """重置回放位置到开头"""
        self.step_index = 0


# 全局回放器实例
replay_player = ReplayPlayer()
