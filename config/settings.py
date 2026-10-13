import os

# ===================== 基础路径配置 =====================
# 项目根目录绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 各业务目录路径
DATA_DIR = os.path.join(BASE_DIR, "data")          # 测试数据目录
OUTPUT_DIR = os.path.join(BASE_DIR, "output")      # 输出文件目录
LOGS_DIR = os.path.join(BASE_DIR, "logs")          # 日志文件目录
STORAGE_DIR = os.path.join(BASE_DIR, "storage")    # 数据库文件目录

# 自动创建目录，避免运行时报错
for path in [DATA_DIR, OUTPUT_DIR, LOGS_DIR, STORAGE_DIR]:
    os.makedirs(path, exist_ok=True)

# ===================== 数据库配置 =====================
# SQLite 数据库文件路径
DB_PATH = os.path.join(STORAGE_DIR, "agentflow.db")

# ===================== 大模型配置 =====================
LLM_MODEL_NAME = "qwen2:7b"       # 使用的大模型名称
LLM_TEMPERATURE = 0.7             # 模型温度，越低越稳定
LLM_TIMEOUT = 60                  # 模型调用超时时间（秒）

# ===================== 任务执行配置 =====================
MAX_RETRY_COUNT = 3               # 轻微异常最大重试次数
RETRY_BACKOFF_BASE = 2            # 指数退避基数（秒）
MAX_NODE_ITERATION = 5            # 单节点最大循环次数，防止死循环

# ===================== 快照配置 =====================
SNAPSHOT_BEFORE_NODE = True       # 节点执行前是否拍快照
SNAPSHOT_AFTER_NODE = True        # 节点执行后是否拍快照
MAX_SNAPSHOT_PER_TASK = 20        # 单个任务最多保存快照数

# ===================== 异常治理配置 =====================
# 异常级别定义
EXCEPTION_LEVEL_MINOR = "minor"       # 轻微异常：自动重试
EXCEPTION_LEVEL_GENERAL = "general"   # 一般异常：降级执行
EXCEPTION_LEVEL_SEVERE = "severe"     # 严重异常：暂停+人工介入

# 轻微异常重试配置
MINOR_RETRY_MAX = 3                   # 最大重试次数
RETRY_BACKOFF_BASE = 1                # 指数退避基数（秒）

# 可自动重试的错误类型
RETRYABLE_ERRORS = [
    "TimeoutError",
    "ConnectionError",
    "NetworkError",
    "RateLimitError"
]
