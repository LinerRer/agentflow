import sqlite3
import json
import uuid
from datetime import datetime
from config.settings import DB_PATH
from storage.models import init_database


class BaseDAO:
    """基础DAO类，封装通用数据库操作"""

    def __init__(self):
        # 初始化数据库，确保表存在
        init_database()

    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # 让查询结果可以通过字段名访问
        return conn

    def _execute(self, sql, params=()):
        """执行写操作"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        conn.close()

    def _query_one(self, sql, params=()):
        """查询单条记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None

    def _query_all(self, sql, params=()):
        """查询所有记录"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]


class TaskDAO(BaseDAO):
    """任务数据访问类"""

    def create_task(self, task_id, task_name, task_type, description=""):
        """创建新任务"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = """
        INSERT INTO tasks (task_id, task_name, task_type, status, create_time, description)
        VALUES (?, ?, ?, 'pending', ?, ?)
        """
        self._execute(sql, (task_id, task_name, task_type, now, description))

    def update_task_status(self, task_id, status, current_node=None):
        """更新任务状态和当前节点"""
        sql = "UPDATE tasks SET status = ?"
        params = [status]

        if current_node:
            sql += ", current_node = ?"
            params.append(current_node)

        sql += " WHERE task_id = ?"
        params.append(task_id)
        self._execute(sql, tuple(params))

    def get_task(self, task_id):
        """根据ID获取任务"""
        sql = "SELECT * FROM tasks WHERE task_id = ?"
        return self._query_one(sql, (task_id,))

    def list_tasks(self, status=None):
        """获取任务列表，可按状态筛选"""
        sql = "SELECT * FROM tasks"
        if status:
            sql += " WHERE status = ?"
            return self._query_all(sql, (status,))
        return self._query_all(sql)


class SnapshotDAO(BaseDAO):
    """状态快照数据访问类"""

    def save_snapshot(self, task_id, node_name, snapshot_type, version, state_data, state_hash=""):
        """保存状态快照"""
        snapshot_id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 状态数据转JSON字符串存储
        state_json = json.dumps(state_data, ensure_ascii=False)

        sql = """
        INSERT INTO snapshots (snapshot_id, task_id, node_name, snapshot_type, version, state_data, create_time, state_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(sql, (snapshot_id, task_id, node_name, snapshot_type, version, state_json, now, state_hash))
        return snapshot_id

    def get_latest_snapshot(self, task_id):
        """获取任务最新的快照"""
        sql = """
        SELECT * FROM snapshots 
        WHERE task_id = ? 
        ORDER BY version DESC, create_time DESC 
        LIMIT 1
        """
        result = self._query_one(sql, (task_id,))
        if result:
            # JSON字符串转回字典
            result["state_data"] = json.loads(result["state_data"])
        return result

    def get_snapshot_by_version(self, task_id, version):
        """根据版本号获取快照"""
        sql = "SELECT * FROM snapshots WHERE task_id = ? AND version = ?"
        result = self._query_one(sql, (task_id, version))
        if result:
            result["state_data"] = json.loads(result["state_data"])
        return result


class LogDAO(BaseDAO):
    """执行日志数据访问类"""

    def add_log(self, task_id, trace_id, log_level, log_type, content, node_name=None, duration=0):
        """添加执行日志"""
        log_id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sql = """
        INSERT INTO execution_logs (log_id, task_id, trace_id, node_name, log_level, log_type, content, create_time, duration)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(sql, (log_id, task_id, trace_id, node_name, log_level, log_type, content, now, duration))
        return log_id

    def get_task_logs(self, task_id):
        """获取任务的所有日志，按时间排序"""
        sql = "SELECT * FROM execution_logs WHERE task_id = ? ORDER BY create_time ASC"
        return self._query_all(sql, (task_id,))


class ExceptionDAO(BaseDAO):
    """异常数据访问类"""

    def add_exception(self, task_id, node_name, exception_type, error_type, error_message, error_stack=""):
        """记录异常"""
        exception_id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sql = """
        INSERT INTO exceptions (exception_id, task_id, node_name, exception_type, error_type, error_message, error_stack, create_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(sql,
                      (exception_id, task_id, node_name, exception_type, error_type, error_message, error_stack, now))
        return exception_id

    def get_task_exceptions(self, task_id):
        """获取任务的所有异常"""
        sql = "SELECT * FROM exceptions WHERE task_id = ? ORDER BY create_time DESC"
        return self._query_all(sql, (task_id,))


# 全局DAO实例，后续直接导入使用
task_dao = TaskDAO()
snapshot_dao = SnapshotDAO()
log_dao = LogDAO()
exception_dao = ExceptionDAO()
