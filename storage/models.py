import sqlite3
from config.settings import DB_PATH

# ===================== 建表SQL语句 =====================
# 任务表：存储所有任务的元信息
CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,           -- 任务唯一ID
    task_name TEXT NOT NULL,            -- 任务名称
    task_type TEXT NOT NULL,            -- 任务类型
    status TEXT NOT NULL,               -- 任务状态：pending/running/paused/failed/completed
    current_node TEXT,                  -- 当前执行到的节点
    create_time TEXT NOT NULL,          -- 创建时间
    start_time TEXT,                    -- 开始执行时间
    end_time TEXT,                      -- 结束时间
    priority INTEGER DEFAULT 1,         -- 优先级
    description TEXT                    -- 任务描述
);
"""

# 状态快照表：存储节点执行前后的状态快照
CREATE_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,       -- 快照唯一ID
    task_id TEXT NOT NULL,              -- 所属任务ID
    node_name TEXT NOT NULL,            -- 对应节点名称
    snapshot_type TEXT NOT NULL,        -- 快照类型：before(执行前)/after(执行后)
    version INTEGER NOT NULL,           -- 快照版本号，递增
    state_data TEXT NOT NULL,           -- 状态数据JSON字符串
    create_time TEXT NOT NULL,          -- 创建时间
    state_hash TEXT,                    -- 状态哈希，用于校验
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
"""

# 执行日志表：全链路执行轨迹
CREATE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS execution_logs (
    log_id TEXT PRIMARY KEY,            -- 日志唯一ID
    task_id TEXT NOT NULL,              -- 所属任务ID
    trace_id TEXT NOT NULL,             -- 全链路追踪ID
    node_name TEXT,                     -- 所属节点
    log_level TEXT NOT NULL,            -- 日志级别：info/warn/error/debug
    log_type TEXT NOT NULL,             -- 日志类型：node_start/node_end/tool_call/system
    content TEXT NOT NULL,              -- 日志内容
    create_time TEXT NOT NULL,          -- 日志时间
    duration REAL,                      -- 耗时（秒）
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
"""

# 异常表：存储所有异常信息
CREATE_EXCEPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS exceptions (
    exception_id TEXT PRIMARY KEY,      -- 异常唯一ID
    task_id TEXT NOT NULL,              -- 所属任务ID
    node_name TEXT NOT NULL,            -- 发生异常的节点
    exception_type TEXT NOT NULL,       -- 异常级别：minor/general/severe
    error_type TEXT NOT NULL,           -- 错误类型
    error_message TEXT NOT NULL,        -- 错误信息
    error_stack TEXT,                   -- 完整错误栈
    retry_count INTEGER DEFAULT 0,      -- 已重试次数
    create_time TEXT NOT NULL,          -- 发生时间
    handled INTEGER DEFAULT 0,          -- 是否已处理 0否1是
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
"""


def init_database():
    """初始化数据库，创建所有表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 执行建表语句
    cursor.execute(CREATE_TASKS_TABLE)
    cursor.execute(CREATE_SNAPSHOTS_TABLE)
    cursor.execute(CREATE_LOGS_TABLE)
    cursor.execute(CREATE_EXCEPTIONS_TABLE)

    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成，所有表创建成功")


if __name__ == "__main__":
    init_database()
