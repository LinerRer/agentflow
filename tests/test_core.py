"""
AgentFlow 核心模块单元测试
覆盖：状态模型、事件总线、异常处理器、快照管理器、DAO层、执行器装饰器、回放器
"""
import os
import sys
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# 把项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ===================== 测试夹具：临时数据库 =====================
@pytest.fixture
def temp_db():
    """创建临时数据库，测试完自动删除"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    # patch 数据库路径
    with patch("config.settings.DB_PATH", db_path), \
         patch("storage.models.DB_PATH", db_path), \
         patch("storage.dao.DB_PATH", db_path):
        # 重新导入，确保用临时库
        import importlib
        import storage.models as models_mod
        import storage.dao as dao_mod
        importlib.reload(models_mod)
        importlib.reload(dao_mod)
        models_mod.init_database()
        yield dao_mod

    os.unlink(db_path)


# ===================== 1. 状态模型测试 =====================
class TestStateModel:
    def test_init_task_state_contains_all_fields(self):
        from core.executor import init_task_state
        state = init_task_state(
            task_id="test-001",
            task_name="测试任务",
            task_type="data_analysis",
            user_input="测试需求",
            trace_id="trace-001"
        )
        assert state["task_id"] == "test-001"
        assert state["task_name"] == "测试任务"
        assert state["task_type"] == "data_analysis"
        assert state["user_input"] == "测试需求"
        assert state["trace_id"] == "trace-001"
        assert state["status"] == "pending"
        assert state["iteration"] == 0
        assert state["error_count"] == 0
        assert state["current_node"] == ""
        assert "context" in state
        assert "start_time" in state

    def test_init_task_state_business_fields_empty(self):
        from core.executor import init_task_state
        state = init_task_state("t1", "n1", "type1", "input1", "tr1")
        assert state["task_plan"] == ""
        assert state["analysis_result"] == ""
        assert state["output_content"] == ""


# ===================== 2. 事件总线测试 =====================
class TestEventBus:
    def test_subscribe_and_publish(self):
        from core.event_bus import EventBus, Event
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test.event", handler)
        bus.publish(Event("test.event", "source1", {"key": "value"}))

        assert len(received) == 1
        assert received[0].event_type == "test.event"
        assert received[0].source == "source1"
        assert received[0].data == {"key": "value"}
        assert received[0].event_id  # 有唯一ID
        assert received[0].timestamp  # 有时间戳

    def test_multiple_subscribers(self):
        from core.event_bus import EventBus, Event
        bus = EventBus()
        calls = []

        def h1(e): calls.append("h1")
        def h2(e): calls.append("h2")

        bus.subscribe("evt", h1)
        bus.subscribe("evt", h2)
        bus.publish(Event("evt", "s", {}))

        assert calls == ["h1", "h2"]

    def test_unsubscribe(self):
        from core.event_bus import EventBus, Event
        bus = EventBus()
        calls = []

        def h(e): calls.append(1)

        bus.subscribe("evt", h)
        bus.unsubscribe("evt", h)
        bus.publish(Event("evt", "s", {}))

        assert calls == []

    def test_publish_no_subscribers_no_error(self):
        from core.event_bus import EventBus, Event
        bus = EventBus()
        # 没有订阅者，发布不应报错
        bus.publish(Event("nonexistent", "s", {}))

    def test_subscriber_exception_isolated(self):
        """一个订阅者抛异常，不影响其他订阅者和总线"""
        from core.event_bus import EventBus, Event
        bus = EventBus()
        calls = []

        def bad_handler(e):
            raise Exception("boom")
        def good_handler(e):
            calls.append("ok")

        bus.subscribe("evt", bad_handler)
        bus.subscribe("evt", good_handler)
        bus.publish(Event("evt", "s", {}))

        assert calls == ["ok"]  # 好的订阅者仍然执行了


# ===================== 3. 异常分级处理器测试 =====================
class TestExceptionHandler:
    def test_classify_timeout_as_minor(self):
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        level = h.classify_exception("TimeoutError", "请求超时")
        assert level == "minor"

    def test_classify_connection_as_minor(self):
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        level = h.classify_exception("ConnectionError", "连接失败")
        assert level == "minor"

    def test_classify_retryable_error_type(self):
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        level = h.classify_exception("RateLimitError", "限流")
        assert level == "minor"

    def test_classify_param_error_as_general(self):
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        level = h.classify_exception("ValueError", "参数错误")
        assert level == "general"

    def test_classify_format_error_as_general(self):
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        level = h.classify_exception("ValueError", "数据格式不对")
        assert level == "general"

    def test_classify_default_general(self):
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        level = h.classify_exception("UnknownError", "未知错误")
        assert level == "general"

    def test_minor_exception_returns_retry(self):
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        result = h.handle_exception("t1", "node1", "TimeoutError", "超时")
        assert result["action"] == "retry"
        assert result["retry_count"] == 1
        assert result["wait_time"] >= 0

    def test_minor_exception_exponential_backoff(self):
        """指数退避：wait_time = 基数^已重试次数，配置基数为1所以每次都是1秒"""
        from core.exception_handler import ExceptionHandler
        from config.settings import RETRY_BACKOFF_BASE
        h = ExceptionHandler()
        r1 = h.handle_exception("t1", "n1", "TimeoutError", "超时")
        r2 = h.handle_exception("t1", "n1", "TimeoutError", "超时")
        r3 = h.handle_exception("t1", "n1", "TimeoutError", "超时")
        # 配置基数为1，所以 1^0=1, 1^1=1, 1^2=1
        assert r1["wait_time"] == RETRY_BACKOFF_BASE ** 0
        assert r2["wait_time"] == RETRY_BACKOFF_BASE ** 1
        assert r3["wait_time"] == RETRY_BACKOFF_BASE ** 2

    def test_minor_exception_retry_exhausted_skip(self):
        """重试次数耗尽后升级为跳过"""
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        # 重试3次后第4次应该跳过
        for _ in range(3):
            h.handle_exception("t1", "n1", "TimeoutError", "超时")
        result = h.handle_exception("t1", "n1", "TimeoutError", "超时")
        assert result["action"] == "skip"

    def test_general_exception_returns_skip(self):
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        result = h.handle_exception("t1", "n1", "ValueError", "参数错误")
        assert result["action"] == "skip"

    def test_retry_key_isolated_per_task_node(self):
        """不同任务/节点的重试计数互相隔离"""
        from core.exception_handler import ExceptionHandler
        h = ExceptionHandler()
        h.handle_exception("t1", "n1", "TimeoutError", "超时")  # t1:n1 第1次
        result = h.handle_exception("t2", "n1", "TimeoutError", "超时")  # t2:n1 应该还是第1次
        assert result["retry_count"] == 1


# ===================== 4. 快照管理器测试 =====================
class TestSnapshotManager:
    def test_calc_state_hash_consistent(self, temp_db):
        from core.snapshot import SnapshotManager
        mgr = SnapshotManager()
        state = {"a": 1, "b": "test"}
        h1 = mgr._calc_state_hash(state)
        h2 = mgr._calc_state_hash(state)
        assert h1 == h2
        assert len(h1) == 32  # MD5长度

    def test_calc_state_hash_changes_when_state_changes(self, temp_db):
        from core.snapshot import SnapshotManager
        mgr = SnapshotManager()
        h1 = mgr._calc_state_hash({"a": 1})
        h2 = mgr._calc_state_hash({"a": 2})
        assert h1 != h2

    def test_save_before_node_returns_id(self, temp_db):
        from core.snapshot import SnapshotManager
        mgr = SnapshotManager()
        sid = mgr.save_before_node("t1", "node1", {"data": "before"})
        assert sid is not None
        assert len(sid) > 0

    def test_save_after_node_returns_id(self, temp_db):
        from core.snapshot import SnapshotManager
        mgr = SnapshotManager()
        sid = mgr.save_after_node("t1", "node1", {"data": "after"})
        assert sid is not None

    def test_version_increments(self, temp_db):
        from core.snapshot import SnapshotManager
        mgr = SnapshotManager()
        mgr.save_before_node("t1", "n1", {})  # v1
        mgr.save_after_node("t1", "n1", {})   # v2
        mgr.save_before_node("t1", "n2", {})  # v3
        latest = temp_db.snapshot_dao.get_latest_snapshot("t1")
        assert latest["version"] == 3

    def test_restore_latest(self, temp_db):
        from core.snapshot import SnapshotManager
        mgr = SnapshotManager()
        mgr.save_before_node("t1", "n1", {"step": 1})
        mgr.save_after_node("t1", "n1", {"step": 2})
        state = mgr.restore_latest("t1")
        assert state["step"] == 2

    def test_restore_by_version(self, temp_db):
        from core.snapshot import SnapshotManager
        mgr = SnapshotManager()
        mgr.save_before_node("t1", "n1", {"step": 1})
        mgr.save_after_node("t1", "n1", {"step": 2})
        state_v1 = mgr.restore_by_version("t1", 1)
        state_v2 = mgr.restore_by_version("t1", 2)
        assert state_v1["step"] == 1
        assert state_v2["step"] == 2

    def test_restore_nonexistent_raises(self, temp_db):
        from core.snapshot import SnapshotManager
        mgr = SnapshotManager()
        with pytest.raises(Exception):
            mgr.restore_latest("nonexistent")


# ===================== 5. DAO 层测试 =====================
class TestTaskDAO:
    def test_create_and_get_task(self, temp_db):
        dao = temp_db.task_dao
        dao.create_task("t1", "任务1", "data_analysis", "描述1")
        task = dao.get_task("t1")
        assert task is not None
        assert task["task_id"] == "t1"
        assert task["task_name"] == "任务1"
        assert task["status"] == "pending"

    def test_list_tasks(self, temp_db):
        dao = temp_db.task_dao
        dao.create_task("t1", "任务1", "type1", "")
        dao.create_task("t2", "任务2", "type2", "")
        tasks = dao.list_tasks()
        assert len(tasks) == 2

    def test_update_task_status(self, temp_db):
        dao = temp_db.task_dao
        dao.create_task("t1", "任务1", "type1", "")
        dao.update_task_status("t1", "running", "node1")
        task = dao.get_task("t1")
        assert task["status"] == "running"
        assert task["current_node"] == "node1"

    def test_get_nonexistent_task_returns_none(self, temp_db):
        dao = temp_db.task_dao
        assert dao.get_task("nonexistent") is None


class TestLogDAO:
    def test_add_and_get_logs(self, temp_db):
        dao = temp_db.log_dao
        dao.add_log("t1", "tr1", "info", "node_start", "节点开始", node_name="n1")
        dao.add_log("t1", "tr1", "info", "node_end", "节点结束", node_name="n1", duration=1.5)
        logs = dao.get_task_logs("t1")
        assert len(logs) == 2
        assert logs[0]["log_type"] == "node_start"
        assert logs[1]["duration"] == 1.5


class TestExceptionDAO:
    def test_add_and_get_exceptions(self, temp_db):
        dao = temp_db.exception_dao
        dao.add_exception("t1", "n1", "general", "ValueError", "参数错误", "stack trace")
        excs = dao.get_task_exceptions("t1")
        assert len(excs) == 1
        assert excs[0]["error_type"] == "ValueError"
        assert excs[0]["error_stack"] == "stack trace"


class TestSnapshotDAO:
    def test_save_and_get_latest(self, temp_db):
        dao = temp_db.snapshot_dao
        dao.save_snapshot("t1", "n1", "before", 1, {"a": 1}, "hash1")
        dao.save_snapshot("t1", "n1", "after", 2, {"a": 2}, "hash2")
        latest = dao.get_latest_snapshot("t1")
        assert latest["version"] == 2
        assert latest["state_data"] == {"a": 2}

    def test_get_by_version(self, temp_db):
        dao = temp_db.snapshot_dao
        dao.save_snapshot("t1", "n1", "before", 1, {"v": 1}, "h1")
        snap = dao.get_snapshot_by_version("t1", 1)
        assert snap["state_data"] == {"v": 1}


# ===================== 6. 执行器装饰器测试 =====================
class TestNodeExecutor:
    def test_normal_execution_writes_logs_and_snapshots(self, temp_db):
        """正常执行的节点应该自动写开始/结束日志和前后快照"""
        from core.executor import node_executor, init_task_state

        @node_executor("test_node")
        def my_node(state):
            state["output_content"] = "done"
            state["status"] = "completed"
            return state

        state = init_task_state("t1", "测试", "type", "input", "tr1")
        result = my_node(state)

        assert result["output_content"] == "done"
        # 检查日志写入
        logs = temp_db.log_dao.get_task_logs("t1")
        log_types = [l["log_type"] for l in logs]
        assert "node_start" in log_types
        assert "node_end" in log_types
        # 检查快照写入
        snaps = temp_db.snapshot_dao._query_all(
            "SELECT * FROM snapshots WHERE task_id=?", ("t1",)
        )
        snap_types = [s["snapshot_type"] for s in snaps]
        assert "before" in snap_types
        assert "after" in snap_types

    def test_exception_retries_then_skips(self, temp_db):
        """节点抛异常应该自动重试，重试耗尽后标记跳过"""
        from core.executor import node_executor, init_task_state

        call_count = {"n": 0}

        @node_executor("fail_node")
        def failing_node(state):
            call_count["n"] += 1
            raise ValueError("总是失败")

        state = init_task_state("t1", "测试", "type", "input", "tr1")
        result = failing_node(state)

        # 1次正常 + 3次重试 = 4次调用
        assert call_count["n"] == 4
        # 异常被记录
        excs = temp_db.exception_dao.get_task_exceptions("t1")
        assert len(excs) > 0
        # 日志里有跳过记录
        logs = temp_db.log_dao.get_task_logs("t1")
        assert any(l["log_type"] == "node_skip" for l in logs)

    def test_preserves_function_name(self):
        """装饰器应该保留原函数名"""
        from core.executor import node_executor

        @node_executor("n1")
        def my_special_node(state):
            return state

        assert my_special_node.__name__ == "my_special_node"

    def test_error_count_increments(self, temp_db):
        from core.executor import node_executor, init_task_state

        @node_executor("fail_node")
        def failing_node(state):
            raise ValueError("fail")

        state = init_task_state("t1", "测试", "type", "input", "tr1")
        result = failing_node(state)
        assert result["error_count"] > 0


# ===================== 7. 回放器测试 =====================
class TestReplayPlayer:
    def _setup_task_with_data(self, temp_db):
        """辅助方法：创建一个有完整日志和快照的任务"""
        task_dao = temp_db.task_dao
        log_dao = temp_db.log_dao
        snap_dao = temp_db.snapshot_dao

        task_dao.create_task("t1", "测试任务", "data_analysis", "描述")
        task_dao.update_task_status("t1", "completed", "report_generate")

        # 节点1
        log_dao.add_log("t1", "tr1", "info", "node_start", "节点1开始", node_name="n1")
        snap_dao.save_snapshot("t1", "n1", "before", 1, {"step": 0}, "h1")
        log_dao.add_log("t1", "tr1", "info", "node_end", "节点1结束", node_name="n1", duration=1.0)
        snap_dao.save_snapshot("t1", "n1", "after", 2, {"step": 1}, "h2")

        # 节点2
        log_dao.add_log("t1", "tr1", "info", "node_start", "节点2开始", node_name="n2")
        snap_dao.save_snapshot("t1", "n2", "before", 3, {"step": 1}, "h3")
        log_dao.add_log("t1", "tr1", "info", "node_end", "节点2结束", node_name="n2", duration=2.0)
        snap_dao.save_snapshot("t1", "n2", "after", 4, {"step": 2}, "h4")

    def test_load_task_builds_steps(self, temp_db):
        from core.replay import ReplayPlayer
        self._setup_task_with_data(temp_db)

        player = ReplayPlayer()
        player.load_task("t1")
        assert len(player.node_steps) == 2
        assert player.node_steps[0]["node_name"] == "n1"
        assert player.node_steps[1]["node_name"] == "n2"

    def test_step_forward(self, temp_db):
        from core.replay import ReplayPlayer
        self._setup_task_with_data(temp_db)

        player = ReplayPlayer()
        player.load_task("t1")
        step1 = player.step_forward()
        assert step1["finished"] is False
        assert step1["step"] == 1
        assert step1["node_name"] == "n1"

        step2 = player.step_forward()
        assert step2["step"] == 2

        step3 = player.step_forward()
        assert step3["finished"] is True

    def test_play_all(self, temp_db):
        from core.replay import ReplayPlayer
        self._setup_task_with_data(temp_db)

        player = ReplayPlayer()
        player.load_task("t1")
        all_steps = player.play_all()
        assert len(all_steps) == 2
        assert all_steps[0]["step"] == 1
        assert all_steps[1]["step"] == 2

    def test_reset(self, temp_db):
        from core.replay import ReplayPlayer
        self._setup_task_with_data(temp_db)

        player = ReplayPlayer()
        player.load_task("t1")
        player.step_forward()
        player.step_forward()
        player.reset()
        assert player.step_index == 0

    def test_step_has_before_after_state(self, temp_db):
        from core.replay import ReplayPlayer
        self._setup_task_with_data(temp_db)

        player = ReplayPlayer()
        player.load_task("t1")
        step = player.node_steps[0]
        assert "before_state" in step
        assert "after_state" in step
        assert step["before_state"]["step"] == 0
        assert step["after_state"]["step"] == 1

    def test_load_nonexistent_task_raises(self, temp_db):
        from core.replay import ReplayPlayer
        player = ReplayPlayer()
        with pytest.raises(Exception):
            player.load_task("nonexistent")


# ===================== 8. 追踪管理器测试 =====================
class TestTraceManager:
    def test_get_task_trace(self, temp_db):
        from core.trace import TraceManager
        task_dao = temp_db.task_dao
        log_dao = temp_db.log_dao

        task_dao.create_task("t1", "任务1", "type1", "desc")
        log_dao.add_log("t1", "tr1", "info", "node_start", "开始", node_name="n1")

        mgr = TraceManager()
        trace = mgr.get_task_trace("t1")
        assert "task" in trace
        assert len(trace["logs"]) == 1
        assert trace["task"]["task_id"] == "t1"

    def test_get_task_trace_nonexistent(self, temp_db):
        from core.trace import TraceManager
        mgr = TraceManager()
        result = mgr.get_task_trace("nonexistent")
        assert "error" in result

    def test_get_full_trace(self, temp_db):
        from core.trace import TraceManager
        task_dao = temp_db.task_dao
        log_dao = temp_db.log_dao

        task_dao.create_task("t1", "任务1", "type1", "desc")
        log_dao.add_log("t1", "tr1", "info", "node_start", "开始", node_name="n1")
        log_dao.add_log("t1", "tr1", "info", "node_end", "结束", node_name="n1")

        mgr = TraceManager()
        full = mgr.get_full_trace("tr1")
        assert full["task_count"] == 1
        assert full["log_count"] == 2

    def test_get_full_trace_nonexistent(self, temp_db):
        from core.trace import TraceManager
        mgr = TraceManager()
        result = mgr.get_full_trace("nonexistent")
        assert "error" in result


# ===================== 9. 子任务管理器测试 =====================
class TestSubtaskManager:
    def test_create_subtask_inherits_trace_id(self, temp_db):
        from core.subtask import SubtaskManager
        from core.executor import init_task_state

        parent = init_task_state("parent1", "父任务", "type", "input", "trace-abc")
        mgr = SubtaskManager()
        sub = mgr.create_subtask(parent, "子任务1", "sub_type", "子输入")

        assert sub["trace_id"] == "trace-abc"  # 继承父任务trace_id
        assert sub["task_id"] != "parent1"  # 独立task_id
        assert sub["context"]["parent_task_id"] == "parent1"

    def test_aggregate_results(self, temp_db):
        from core.subtask import SubtaskManager
        from core.executor import init_task_state

        parent = init_task_state("p1", "父", "t", "i", "tr")
        mgr = SubtaskManager()

        sub_results = [
            {"task_id": "s1", "task_name": "子1", "status": "completed", "output_content": "结果1"},
            {"task_id": "s2", "task_name": "子2", "status": "failed", "message": "失败了"},
        ]
        result = mgr.aggregate_results(parent, sub_results)

        assert len(result["context"]["subtask_results"]) == 2
        assert result["context"]["subtask_results"][0]["output"] == "结果1"
        assert result["context"]["subtask_results"][1]["status"] == "failed"


# ===================== 10. 工作流调度器测试 =====================
class TestWorkflowScheduler:
    def test_register_and_build(self):
        from core.workflow_scheduler import WorkflowScheduler

        scheduler = WorkflowScheduler()

        def node_a(state):
            return state
        def node_b(state):
            return state

        scheduler.register_node("a", node_a)
        scheduler.register_node("b", node_b)
        scheduler.set_entry("a")
        scheduler.add_route("a", "b")
        scheduler.add_route("b", "END")

        app = scheduler.build()
        assert app is not None

    def test_build_without_entry_raises(self):
        from core.workflow_scheduler import WorkflowScheduler
        scheduler = WorkflowScheduler()
        scheduler.register_node("a", lambda s: s)
        with pytest.raises(Exception):
            scheduler.build()
