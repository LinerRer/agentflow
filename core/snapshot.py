import hashlib
import json
from storage.dao import snapshot_dao
from config.settings import SNAPSHOT_BEFORE_NODE, SNAPSHOT_AFTER_NODE, MAX_SNAPSHOT_PER_TASK


class SnapshotManager:
    """
    状态快照管理器
    负责状态的快照保存、恢复、版本管理
    """

    def __init__(self):
        self.version_counter = {}  # 每个任务的快照版本计数器

    def _get_next_version(self, task_id: str) -> int:
        """获取下一个快照版本号"""
        if task_id not in self.version_counter:
            # 从数据库查询当前最大版本
            latest = snapshot_dao.get_latest_snapshot(task_id)
            self.version_counter[task_id] = latest["version"] if latest else 0
        self.version_counter[task_id] += 1
        return self.version_counter[task_id]

    def _calc_state_hash(self, state: dict) -> str:
        """计算状态数据的哈希值，用于校验"""
        state_str = json.dumps(state, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(state_str.encode("utf-8")).hexdigest()

    def save_before_node(self, task_id: str, node_name: str, state: dict) -> str:
        """
        节点执行前保存快照
        返回快照ID
        """
        if not SNAPSHOT_BEFORE_NODE:
            return ""

        version = self._get_next_version(task_id)
        state_hash = self._calc_state_hash(state)

        snapshot_id = snapshot_dao.save_snapshot(
            task_id=task_id,
            node_name=node_name,
            snapshot_type="before",
            version=version,
            state_data=state,
            state_hash=state_hash
        )
        return snapshot_id

    def save_after_node(self, task_id: str, node_name: str, state: dict) -> str:
        """
        节点执行后保存快照
        返回快照ID
        """
        if not SNAPSHOT_AFTER_NODE:
            return ""

        version = self._get_next_version(task_id)
        state_hash = self._calc_state_hash(state)

        snapshot_id = snapshot_dao.save_snapshot(
            task_id=task_id,
            node_name=node_name,
            snapshot_type="after",
            version=version,
            state_data=state,
            state_hash=state_hash
        )
        return snapshot_id

    def restore_latest(self, task_id: str) -> dict:
        """恢复任务最新的快照状态"""
        latest = snapshot_dao.get_latest_snapshot(task_id)
        if not latest:
            raise Exception(f"任务 {task_id} 没有可用的快照")
        return latest["state_data"]

    def restore_by_version(self, task_id: str, version: int) -> dict:
        """根据版本号恢复状态"""
        snapshot = snapshot_dao.get_snapshot_by_version(task_id, version)
        if not snapshot:
            raise Exception(f"任务 {task_id} 版本 {version} 的快照不存在")
        return snapshot["state_data"]


# 全局快照管理器实例
snapshot_manager = SnapshotManager()
