import time
from config.settings import (
    EXCEPTION_LEVEL_MINOR,
    EXCEPTION_LEVEL_GENERAL,
    EXCEPTION_LEVEL_SEVERE,
    MINOR_RETRY_MAX,
    RETRY_BACKOFF_BASE,
    RETRYABLE_ERRORS
)
from storage.dao import exception_dao


class ExceptionHandler:
    """
    异常分级处理器
    根据异常类型和级别执行不同的处理策略
    """

    def __init__(self):
        self.retry_counts = {}  # 记录每个任务节点的重试次数

    def _get_retry_key(self, task_id: str, node_name: str) -> str:
        """生成重试计数的key"""
        return f"{task_id}:{node_name}"

    def classify_exception(self, error_type: str, error_message: str) -> str:
        """
        判断异常级别
        返回：minor/general/severe
        """
        # 可重试的网络/超时类错误 → 轻微异常
        if error_type in RETRYABLE_ERRORS or "超时" in error_message or "连接" in error_message:
            return EXCEPTION_LEVEL_MINOR

        # 参数错误、数据格式错误 → 一般异常
        if "参数" in error_message or "格式" in error_message or "字段" in error_message:
            return EXCEPTION_LEVEL_GENERAL

        # 其他默认一般异常
        return EXCEPTION_LEVEL_GENERAL

    def handle_exception(self, task_id: str, node_name: str, error_type: str, error_message: str) -> dict:
        """
        处理异常，返回处理结果
        返回格式：{"action": "retry/skip/fail", "wait_time": 0, "message": ""}
        """
        # 1. 分级
        level = self.classify_exception(error_type, error_message)

        # 2. 根据级别执行策略
        if level == EXCEPTION_LEVEL_MINOR:
            return self._handle_minor(task_id, node_name, error_type, error_message)
        elif level == EXCEPTION_LEVEL_GENERAL:
            return self._handle_general(task_id, node_name, error_type, error_message)
        else:
            return self._handle_severe(task_id, node_name, error_type, error_message)

    def _handle_minor(self, task_id: str, node_name: str, error_type: str, error_message: str) -> dict:
        """处理轻微异常：自动重试 + 指数退避"""
        key = self._get_retry_key(task_id, node_name)
        count = self.retry_counts.get(key, 0)

        if count < MINOR_RETRY_MAX:
            # 可以重试
            self.retry_counts[key] = count + 1
            wait_time = RETRY_BACKOFF_BASE ** count  # 指数退避

            # 更新异常记录的重试次数
            exceptions = exception_dao.get_task_exceptions(task_id)
            if exceptions:
                latest_id = exceptions[0]["exception_id"]
                # 这里简化处理，实际可以更新重试次数字段

            return {
                "action": "retry",
                "wait_time": wait_time,
                "retry_count": count + 1,
                "message": f"轻微异常，第 {count + 1} 次重试，等待 {wait_time} 秒"
            }
        else:
            # 重试次数耗尽，升级为一般异常
            return {
                "action": "skip",
                "message": "重试次数耗尽，跳过该节点，继续执行"
            }

    def _handle_general(self, task_id: str, node_name: str, error_type: str, error_message: str) -> dict:
        """处理一般异常：降级执行，跳过非核心节点"""
        return {
            "action": "skip",
            "message": "一般异常，跳过当前节点，继续后续流程"
        }

    def _handle_severe(self, task_id: str, node_name: str, error_type: str, error_message: str) -> dict:
        """处理严重异常：暂停任务，等待人工介入"""
        return {
            "action": "fail",
            "message": "严重异常，任务暂停，需要人工介入"
        }


# 全局异常处理器实例
exception_handler = ExceptionHandler()
