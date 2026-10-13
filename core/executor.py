import time
import traceback
from functools import wraps
from storage.dao import log_dao, exception_dao, task_dao
from core.snapshot import snapshot_manager
from config.settings import MAX_RETRY_COUNT


def node_executor(node_name: str):
    """
    节点执行器装饰器
    自动完成：日志记录、状态快照、异常重试、状态持久化
    """

    def decorator(func):
        @wraps(func)
        def wrapper(state):
            trace_id = state.get("trace_id", "")
            task_id = state.get("task_id", "")

            # 1. 记录节点开始日志
            log_dao.add_log(
                task_id=task_id,
                trace_id=trace_id,
                node_name=node_name,
                log_level="info",
                log_type="node_start",
                content=f"节点 [{node_name}] 开始执行"
            )

            # 2. 保存执行前快照
            snapshot_manager.save_before_node(task_id, node_name, state)

            # 3. 执行节点（带异常重试）
            skipped = False
            result_state = state

            for attempt in range(MAX_RETRY_COUNT + 1):
                try:
                    # 执行业务节点
                    result_state = func(state)
                    break

                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e)

                    # 记录异常
                    exception_dao.add_exception(
                        task_id=task_id,
                        node_name=node_name,
                        exception_type="general",
                        error_type=error_type,
                        error_message=error_msg,
                        error_stack=traceback.format_exc()
                    )

                    state["error_count"] = state.get("error_count", 0) + 1

                    if attempt < MAX_RETRY_COUNT:
                        # 还有重试次数，继续重试
                        continue
                    else:
                        # 重试耗尽，标记为跳过
                        skipped = True
                        result_state = state
                        break

            # ===================== 执行后处理 =====================
            duration = round(time.time(), 3) - float(state.get("start_time", time.time()))
            if duration < 0:
                duration = 0.001
            duration = round(duration, 3)

            # 1. 保存执行后快照
            snapshot_manager.save_after_node(task_id, node_name, result_state)

            # 2. 记录结束日志
            if skipped:
                # 节点异常跳过
                log_dao.add_log(
                    task_id=task_id,
                    trace_id=trace_id,
                    node_name=node_name,
                    log_level="warn",
                    log_type="node_skip",
                    content=f"节点 [{node_name}] 执行失败，已跳过",
                    duration=duration
                )
            else:
                # 节点正常完成
                log_dao.add_log(
                    task_id=task_id,
                    trace_id=trace_id,
                    node_name=node_name,
                    log_level="info",
                    log_type="node_end",
                    content=f"节点 [{node_name}] 执行完成，耗时 {duration} 秒",
                    duration=duration
                )

            # 3. 更新任务状态
            if result_state.get("status") == "completed":
                task_dao.update_task_status(task_id, "completed", node_name)
            else:
                task_dao.update_task_status(task_id, "running", node_name)

            return result_state

        return wrapper

    return decorator


def init_task_state(task_id: str, task_name: str, task_type: str, user_input: str, trace_id: str) -> dict:
    """初始化标准任务状态"""
    return {
        "task_id": task_id,
        "task_name": task_name,
        "task_type": task_type,
        "trace_id": trace_id,
        "current_node": "",
        "status": "pending",
        "iteration": 0,
        "error_count": 0,
        "user_input": user_input,
        "task_plan": "",
        "analysis_result": "",
        "output_content": "",
        "context": {},
        "message": "",
        "start_time": time.time()
    }
