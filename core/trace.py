import json
from storage.dao import task_dao, log_dao, snapshot_dao, exception_dao


class TraceManager:
    """
    全链路追踪管理器
    基于 trace_id 聚合所有执行数据，形成完整执行链路
    """

    def get_full_trace(self, trace_id: str) -> dict:
        """
        获取 trace_id 对应的完整执行链路
        返回包含：任务信息、执行日志、状态快照、异常信息
        """
        # 1. 查询该 trace 下的所有任务（含父子任务）
        all_tasks = task_dao._query_all(
            "SELECT * FROM tasks WHERE task_id IN (SELECT DISTINCT task_id FROM execution_logs WHERE trace_id = ?)",
            (trace_id,)
        )

        if not all_tasks:
            return {"error": "trace_id 不存在", "trace_id": trace_id}

        # 2. 按时间排序的完整日志时间线
        all_logs = log_dao._query_all(
            "SELECT * FROM execution_logs WHERE trace_id = ? ORDER BY create_time ASC",
            (trace_id,)
        )

        # 3. 所有状态快照
        all_snapshots = []
        for task in all_tasks:
            snapshots = snapshot_dao._query_all(
                "SELECT * FROM snapshots WHERE task_id = ? ORDER BY version ASC",
                (task["task_id"],)
            )
            # 解析state_data为字典
            for snap in snapshots:
                snap["state_data"] = json.loads(snap["state_data"])
            all_snapshots.extend(snapshots)

        # 4. 所有异常记录
        all_exceptions = []
        for task in all_tasks:
            exceptions = exception_dao.get_task_exceptions(task["task_id"])
            all_exceptions.extend(exceptions)

        # 5. 聚合返回
        return {
            "trace_id": trace_id,
            "task_count": len(all_tasks),
            "tasks": all_tasks,
            "log_count": len(all_logs),
            "logs": all_logs,
            "snapshot_count": len(all_snapshots),
            "snapshots": all_snapshots,
            "exception_count": len(all_exceptions),
            "exceptions": all_exceptions
        }

    def get_task_trace(self, task_id: str) -> dict:
        """根据任务ID获取对应trace的完整链路"""
        task = task_dao.get_task(task_id)
        if not task:
            return {"error": "任务不存在"}

        logs = log_dao.get_task_logs(task_id)
        snapshots = snapshot_dao._query_all(
            "SELECT * FROM snapshots WHERE task_id = ? ORDER BY version ASC",
            (task_id,)
        )
        # 解析state_data为字典
        for snap in snapshots:
            snap["state_data"] = json.loads(snap["state_data"])

        exceptions = exception_dao.get_task_exceptions(task_id)

        return {
            "task": task,
            "logs": logs,
            "snapshots": snapshots,
            "exceptions": exceptions
        }

    def search_by_keyword(self, keyword: str) -> list:
        """按关键词搜索日志内容"""
        sql = """
        SELECT * FROM execution_logs 
        WHERE content LIKE ? 
        ORDER BY create_time DESC 
        LIMIT 50
        """
        return log_dao._query_all(sql, (f"%{keyword}%",))


# 全局追踪管理器实例
trace_manager = TraceManager()
