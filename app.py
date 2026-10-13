import uuid
import streamlit as st
from core.executor import init_task_state
from core.trace import trace_manager
from core.replay import replay_player
from storage.dao import task_dao
from agents.data_analysis_agent import build_analysis_workflow

# ===================== 页面配置 =====================
st.set_page_config(
    page_title="AgentFlow 智能工作流平台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== 全局自定义样式 =====================
st.markdown("""
<style>
/* ===== 全局背景 ===== */
.stApp {
    background: linear-gradient(135deg, #f0f4ff 0%, #f8fafc 50%, #f5f3ff 100%);
}

/* ===== 隐藏默认元素 ===== */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ===== 主内容区 ===== */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 95%;
}

/* ===== 顶部标题渐变条 ===== */
.app-header {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
    padding: 1.8rem 2rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(99, 102, 241, 0.25);
    position: relative;
    overflow: hidden;
}
.app-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
    border-radius: 50%;
}
.app-header h1 {
    color: #ffffff;
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: 1px;
}
.app-header p {
    color: rgba(255,255,255,0.9);
    font-size: 0.95rem;
    margin: 0.4rem 0 0 0;
}

/* ===== 侧边栏 ===== */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    border-right: 1px solid #e2e8f0;
    box-shadow: 2px 0 12px rgba(0, 0, 0, 0.04);
}
section[data-testid="stSidebar"] .stRadio label {
    color: #334155;
    font-weight: 500;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #4f46e5;
}

/* ===== 卡片容器 ===== */
.glass-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* ===== 子标题 ===== */
.section-title {
    color: #4f46e5;
    font-size: 1.15rem;
    font-weight: 600;
    margin-bottom: 1rem;
    padding-left: 0.8rem;
    border-left: 3px solid #6366f1;
}

/* ===== 输入框美化 ===== */
.stTextInput input, .stTextArea textarea {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    color: #1e293b !important;
    padding: 0.7rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}
.stTextInput label, .stTextArea label {
    color: #475569 !important;
    font-weight: 500 !important;
}

/* ===== 按钮美化 ===== */
.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.55rem 1.5rem !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ===== Metric 卡片美化 ===== */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
[data-testid="stMetric"] label {
    color: #64748b !important;
    font-size: 0.85rem !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #1e293b !important;
    font-size: 1.3rem !important;
    font-weight: 700 !important;
}

/* ===== Expander 美化 ===== */
.streamlit-expanderHeader {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    color: #1e293b !important;
    font-weight: 500 !important;
}
.streamlit-expanderContent {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
}

/* ===== 代码块美化 ===== */
.stCodeBlock {
    background: #f1f5f9 !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
}

/* ===== 下拉选择框 ===== */
.stSelectbox > div > div {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    color: #1e293b !important;
}

/* ===== Slider ===== */
.stSlider [data-baseweb="slider"] {
    background: transparent !important;
}
.stSlider [data-baseweb="slider"] > div > div {
    background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
}

/* ===== 提示信息美化 ===== */
.stAlert {
    border-radius: 10px !important;
    border: none !important;
}
.stSuccess {
    background: #f0fdf4 !important;
    color: #166534 !important;
}
.stError {
    background: #fef2f2 !important;
    color: #991b1b !important;
}
.stWarning {
    background: #fffbeb !important;
    color: #92400e !important;
}
.stInfo {
    background: #eef2ff !important;
    color: #3730a3 !important;
}

/* ===== 分割线 ===== */
hr {
    border-color: #e2e8f0 !important;
    margin: 1.5rem 0 !important;
}

/* ===== 报告内容区 ===== */
.report-content {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem;
    color: #1e293b;
    line-height: 1.8;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.report-content h1, .report-content h2, .report-content h3 {
    color: #4f46e5;
}

/* ===== 日志时间线 ===== */
.timeline-item {
    display: flex;
    gap: 1rem;
    padding: 0.8rem 1rem;
    border-left: 2px solid #c7d2fe;
    margin-left: 0.5rem;
    position: relative;
}
.timeline-item::before {
    content: '';
    position: absolute;
    left: -6px;
    top: 1rem;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #6366f1;
}
.timeline-time {
    color: #64748b;
    font-size: 0.8rem;
    min-width: 140px;
    padding-top: 2px;
}
.timeline-level {
    min-width: 60px;
    text-align: center;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 6px;
    height: fit-content;
}
.level-info { background: #eef2ff; color: #4338ca; }
.level-warn { background: #fffbeb; color: #b45309; }
.level-error { background: #fef2f2; color: #b91c1c; }
.timeline-content {
    color: #334155;
    font-size: 0.9rem;
}
.timeline-content strong {
    color: #4f46e5;
}

/* ===== 状态标签 ===== */
.status-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}
.status-completed { background: #dcfce7; color: #166534; }
.status-failed { background: #fee2e2; color: #991b1b; }
.status-running { background: #dbeafe; color: #1e40af; }
.status-pending { background: #f1f5f9; color: #475569; }

/* ===== 空状态提示 ===== */
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: #94a3b8;
}
.empty-state .icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ===================== 顶部标题栏 =====================
st.markdown("""
<div class="app-header">
    <h1>🤖 AgentFlow 智能工作流平台</h1>
    <p>基于 LangGraph 的可观测、可回溯、可调试智能 Agent 平台</p>
</div>
""", unsafe_allow_html=True)

# ===================== 侧边栏：功能导航 =====================
with st.sidebar:
    st.markdown("### 🧭 功能导航")
    page = st.radio(
        "",
        ["📝 新建任务", "📋 任务列表", "🔍 全链路追踪", "⏮️ 执行回放"],
        label_visibility="collapsed"
    )
    st.divider()
    st.markdown("""
    <div style="background: #eef2ff; padding: 1rem; border-radius: 10px; border: 1px solid #c7d2fe;">
        <p style="color:#4338ca; font-size:0.85rem; margin:0;">💡 所有任务自动持久化<br>支持全链路追溯和历史回放</p>
    </div>
    """, unsafe_allow_html=True)

# ===================== 页面1：新建任务 =====================
if page == "📝 新建任务":
    st.markdown('<div class="section-title">📝 新建数据分析任务</div>', unsafe_allow_html=True)

    # 初始化会话状态
    if "last_task_result" not in st.session_state:
        st.session_state.last_task_result = None
        st.session_state.last_task_id = ""
        st.session_state.last_trace_id = ""
        st.session_state.last_input = ""

    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        user_input = st.text_area(
            "请输入你的数据分析需求",
            height=150,
            placeholder="例如：分析2024年电商销售数据的增长趋势，找出核心影响因素",
            value=st.session_state.last_input
        )

        col1, col2 = st.columns([1, 5])
        with col1:
            submit_btn = st.button("🚀 提交任务", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if submit_btn and user_input.strip():
        with st.spinner("⚙️ 任务执行中，请稍候..."):
            task_id = str(uuid.uuid4())
            trace_id = str(uuid.uuid4())

            task_dao.create_task(
                task_id=task_id,
                task_name="数据分析任务",
                task_type="data_analysis",
                description=user_input.strip()
            )

            initial_state = init_task_state(
                task_id=task_id,
                task_name="数据分析任务",
                task_type="data_analysis",
                user_input=user_input.strip(),
                trace_id=trace_id
            )

            workflow = build_analysis_workflow()
            result_state = workflow.invoke(initial_state)

            st.session_state.last_task_result = result_state
            st.session_state.last_task_id = task_id
            st.session_state.last_trace_id = trace_id
            st.session_state.last_input = user_input.strip()

            st.success("✅ 任务执行完成！")

    if st.session_state.last_task_result is not None:
        st.markdown('<div class="section-title">📄 分析报告</div>', unsafe_allow_html=True)
        output = st.session_state.last_task_result.get("output_content", "")
        if output.strip():
            st.markdown(f'<div class="report-content">{output}</div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ 任务执行异常，未生成报告内容，请查看任务日志排查原因")

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("任务ID", st.session_state.last_task_id[:8] + "...")
        with col2:
            st.metric("追踪ID", st.session_state.last_trace_id[:8] + "...")
        with col3:
            status = st.session_state.last_task_result.get("status", "未知")
            st.metric("状态", status)

        col1, col2 = st.columns(2)
        with col1:
            st.caption("任务ID（点击复制）")
            st.code(st.session_state.last_task_id, language=None)
        with col2:
            st.caption("追踪ID（点击复制）")
            st.code(st.session_state.last_trace_id, language=None)


# ===================== 页面2：任务列表 =====================
elif page == "📋 任务列表":
    st.markdown('<div class="section-title">📋 所有任务列表</div>', unsafe_allow_html=True)

    all_tasks = task_dao.list_tasks()

    if not all_tasks:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📭</div>
            <p>暂无任务记录，去新建一个任务吧</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        col1, col2 = st.columns([1, 5])
        with col1:
            status_filter = st.selectbox(
                "按状态筛选",
                ["全部", "pending", "running", "completed", "failed"]
            )

        if status_filter != "全部":
            all_tasks = [t for t in all_tasks if t["status"] == status_filter]

        for task in reversed(all_tasks):
            status_class = f"status-{task['status']}"
            with st.expander(f"📌 {task['task_name']} - {task['task_id'][:12]}..."):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write("**状态**")
                    st.markdown(f'<span class="status-badge {status_class}">{task["status"]}</span>', unsafe_allow_html=True)
                with col2:
                    st.write("**类型**")
                    st.text(task["task_type"])
                with col3:
                    st.write("**创建时间**")
                    st.text(task["create_time"])
                with col4:
                    st.write("**当前节点**")
                    st.text(task["current_node"] or "-")

                st.write("**任务描述**")
                st.text(task["description"])

                trace_data = trace_manager.get_task_trace(task["task_id"])
                trace_id = trace_data["logs"][0]["trace_id"] if trace_data["logs"] else "-"

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📋 复制任务ID", key=f"copy_task_{task['task_id']}"):
                        st.code(task["task_id"], language=None)
                with col2:
                    if st.button("🔗 复制追踪ID", key=f"copy_trace_{task['task_id']}"):
                        st.code(trace_id, language=None)
                with col3:
                    if st.button("📊 查看详细日志", key=f"log_{task['task_id']}"):
                        st.json(trace_data, expanded=False)


# ===================== 页面3：全链路追踪 =====================
elif page == "🔍 全链路追踪":
    st.markdown('<div class="section-title">🔍 全链路追踪</div>', unsafe_allow_html=True)

    # 会话保存查询结果
    if "trace_result" not in st.session_state:
        st.session_state.trace_result = None
        st.session_state.trace_input = ""

    col1, col2 = st.columns([4, 1])
    with col1:
        trace_input = st.text_input("请输入 Trace ID 进行全链路查询", value=st.session_state.trace_input, label_visibility="collapsed", placeholder="请输入 Trace ID...")
    with col2:
        query_btn = st.button("🔍 查询", type="primary", use_container_width=True)

    if query_btn and trace_input.strip():
        trace_id = trace_input.strip()
        for prefix in ["完整追踪ID：", "完整追踪ID:", "追踪ID：", "trace_id:"]:
            trace_id = trace_id.replace(prefix, "")
        trace_id = trace_id.strip()

        st.session_state.trace_input = trace_input

        with st.spinner("查询中..."):
            full_trace = trace_manager.get_full_trace(trace_id)
            st.session_state.trace_result = full_trace

    if st.session_state.trace_result is not None:
        full_trace = st.session_state.trace_result

        if "error" in full_trace:
            st.error(full_trace["error"])
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("关联任务数", full_trace["task_count"])
            with col2:
                st.metric("日志总数", full_trace["log_count"])
            with col3:
                st.metric("快照总数", full_trace["snapshot_count"])
            with col4:
                st.metric("异常总数", full_trace["exception_count"])

            st.markdown('<div class="section-title">📜 执行日志时间线</div>', unsafe_allow_html=True)
            for log in full_trace["logs"]:
                level_class = f"level-{log['log_level']}"
                st.markdown(f"""
                <div class="timeline-item">
                    <div class="timeline-time">{log['create_time']}</div>
                    <div class="timeline-level {level_class}">{log['log_level'].upper()}</div>
                    <div class="timeline-content"><strong>[{log['node_name']}]</strong> {log['content']}</div>
                </div>
                """, unsafe_allow_html=True)

            if full_trace["exceptions"]:
                st.markdown('<div class="section-title">⚠️ 异常记录</div>', unsafe_allow_html=True)
                for exc in full_trace["exceptions"]:
                    with st.expander(f"🚨 {exc['exception_type']} - {exc['error_type']}"):
                        st.error(exc["error_message"])
                        st.code(exc["error_stack"], language="python")


# ===================== 页面4：执行回放 =====================
elif page == "⏮️ 执行回放":
    st.markdown('<div class="section-title">⏮️ 任务执行回放</div>', unsafe_allow_html=True)

    # 会话保存查询结果
    if "replay_result" not in st.session_state:
        st.session_state.replay_result = None
        st.session_state.replay_input = ""

    col1, col2 = st.columns([4, 1])
    with col1:
        task_input = st.text_input("请输入任务ID进行回放", value=st.session_state.replay_input, label_visibility="collapsed", placeholder="请输入任务ID...")
    with col2:
        load_btn = st.button("▶️ 加载回放", type="primary", use_container_width=True)

    if load_btn and task_input.strip():
        task_id = task_input.strip()
        for prefix in ["完整任务ID：", "完整任务ID:", "任务ID：", "task_id:"]:
            task_id = task_id.replace(prefix, "")
        task_id = task_id.strip()

        st.session_state.replay_input = task_input

        try:
            replay_player.load_task(task_id)
            all_steps = replay_player.play_all()
            st.session_state.replay_result = all_steps
            st.success(f"✅ 任务加载成功，共 {len(all_steps)} 个执行步骤")
        except Exception as e:
            st.session_state.replay_result = None
            st.error(f"加载失败：{str(e)}")

    if st.session_state.replay_result is not None:
        all_steps = st.session_state.replay_result

        step_num = st.slider("选择回放步骤", 1, len(all_steps), 1)
        step = all_steps[step_num - 1]

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("节点名称", step["node_name"])
        with col2:
            status_class = f"status-{step['status']}"
            st.metric("执行状态", step["status"])
        with col3:
            st.metric("耗时", f"{step['duration']} 秒")

        st.markdown('<div class="section-title">📊 状态前后对比</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.caption("🔵 执行前状态")
            st.json(step["before_state"], expanded=3)
        with col2:
            st.caption("🟢 执行后状态")
            st.json(step["after_state"], expanded=3)

        st.markdown('<div class="section-title">📝 执行日志</div>', unsafe_allow_html=True)
        st.info(step["start_log"])
        if step["status"] == "completed":
            st.success(step["end_log"])
        else:
            st.error(step["end_log"])
