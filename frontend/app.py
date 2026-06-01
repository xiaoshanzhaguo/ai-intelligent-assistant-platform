import time
from uuid import uuid4

import streamlit as st

from frontend.api_client import (
    clear_indexed_document,
    index_uploaded_document,
    iter_sse_events,
    post_stream_request,
)
from frontend.file_parser import (
    build_non_rag_input_text,
    build_text_fingerprint,
    build_user_display_text,
    extract_text_from_uploaded_file,
)
from frontend.renderers import (
    format_workflow_blocks,
    render_result_actions,
    render_workflow_step_copy_actions,
)
from frontend.state_manager import (
    build_history_for_api,
    ensure_mode_sessions,
    load_mode_sessions,
    save_mode_sessions,
)


# -----------------------------
# 页面基础配置
# -----------------------------
st.set_page_config(
    page_title="AI 内容分析与创作助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}
)

st.title("AI 内容分析与创作助手")


# -----------------------------
# 模式映射
# 前端展示名称 -> 后端 task_type
# persona 先沿用展示名称，便于后端按人设/风格扩展
# -----------------------------
MODE_TO_TASK_TYPE = {
    "内容分析": "summary",
    "结构优化": "rewrite",
    "风格改写": "rewrite",
    "多版本生成": "chat",
    "工作流优化": "workflow"
}

MODE_DESCRIPTIONS = {
    "内容分析": "提炼主题、关键信息和结论",
    "结构优化": "整理表达层次和逻辑结构",
    "风格改写": "保持原意，调整表达语气",
    "多版本生成": "生成不同场景可直接使用的版本",
    "工作流优化": "分步骤总结、分析并提出建议"
}

AVAILABLE_MODES = list(MODE_TO_TASK_TYPE.keys())
mode = st.sidebar.selectbox("选择功能", AVAILABLE_MODES)
st.caption(f"当前模式：{MODE_DESCRIPTIONS[mode]}")

# -----------------------------
# 第一阶段启用 RAG 的模式
# 先只支持：内容分析、工作流优化
# -----------------------------
RAG_ENABLED_MODES = {
    "内容分析",
    "工作流优化"
}

DEFAULT_FILE_MODE_PROMPTS = {
    "内容分析": "请基于上传文档完成内容分析，提炼主题、关键信息和结论。",
    "工作流优化": "请基于上传文档进行工作流优化，分步骤总结、分析并提出建议。"
}

CHAT_INPUT_FILE_TYPES = ["txt", "md", "pdf"]


# -----------------------------
# 支持文件上传分析的模式
# 多版本生成暂不启用文件上传
# -----------------------------
UPLOAD_ENABLED_MODES = {
    "内容分析",
    "结构优化",
    "风格改写",
    "工作流优化"
}


# -----------------------------
# Session State 初始化
# 如果不存在，或被清空为 {}，则重新初始化
# -----------------------------
if "mode_sessions" not in st.session_state or not st.session_state.mode_sessions:
    # 页面初始化时优先从本地历史文件恢复 mode_sessions，不再每次刷新都创建空会话
    st.session_state.mode_sessions = load_mode_sessions(AVAILABLE_MODES)

# 确保所有当前支持的模式都有会话容器
st.session_state.mode_sessions = ensure_mode_sessions(
    st.session_state.mode_sessions,
    AVAILABLE_MODES
)

# -----------------------------
# 用于记录当前模式下，当前 session 的文档是否已经索引过，避免每次发请求都重新索引。
# -----------------------------
if "rag_index_state" not in st.session_state:
    # 记录“每个模式当前已经索引过哪份文档”
    st.session_state.rag_index_state = {}

# 当前模式对应的会话状态
current_session = st.session_state.mode_sessions[mode]
current_session_id = current_session["session_id"]
current_messages = current_session["messages"]


# -----------------------------
# RAG 控件区
# 说明：
# - 控件要放在历史消息前面，否则 Streamlit 重跑后会被历史输出挤到页面下方
# - 即使当前没附加文件，也先给默认值，保证后续 payload 安全
# -----------------------------
use_rag = False
rag_top_k = 3


if mode in RAG_ENABLED_MODES:
    use_rag = st.checkbox(
        "启用文档检索增强（RAG）",
        value=True,
        key=f"use_rag_{mode}"
    )

    if use_rag:
        rag_top_k = st.slider(
            "检索片段数量",
            min_value=1,
            max_value=5,
            value=3,
            key=f"rag_top_k_{mode}"
        )

        st.caption("在附加文档时，系统会先检索相关片段，再交给模型处理。")

        # 取出当前模式对应的索引记录
        current_index_state = st.session_state.rag_index_state.get(mode)
        if current_index_state and current_index_state.get("session_id") == current_session_id:
            file_name = current_index_state.get("file_name", "未命名文件")
            st.caption(f"当前会话已索引文档：{file_name}")


# -----------------------------
# 展示当前模式的历史消息
# assistant 消息支持 markdown，便于工作流分段展示
# 并为 assistant 消息补充：
# - 复制当前结果
# - 导出 Markdown
# -----------------------------
for idx, message in enumerate(current_messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            # 整体结果操作：复制整段结果 + 导出 Markdown
            render_result_actions(
                result_text=message["content"],
                mode_name=mode,
                widget_key_suffix=f"history_{idx}"
            )

            # 如果是 workflow 结果，并且保留了分步结构，则额外支持分步复制
            if mode == "工作流优化" and message.get("workflow_blocks"):
                render_workflow_step_copy_actions(
                    workflow_blocks=message["workflow_blocks"],
                    widget_key_suffix=f"history_steps_{idx}"
                )


# -----------------------------
# 会话控制按钮
# -----------------------------
if st.sidebar.button("新建当前模式聊天"):
    # 先取旧的 session_id, 用于清理后端 RAG 内存索引
    old_session_id = st.session_state.mode_sessions[mode]["session_id"]
    clear_indexed_document(old_session_id)

    # 再重置当前模式会话
    st.session_state.mode_sessions[mode] = {
        "session_id": str(uuid4()),
        "messages": []
    }

    # 同步清理前端记录的索引状态
    st.session_state.rag_index_state.pop(mode, None)
    # 新建当前模式聊天时，同步更新本地历史文件
    save_mode_sessions(st.session_state.mode_sessions)

    st.rerun()

if st.sidebar.button("清空当前模式聊天"):
    # 只清理当前模式 session 对应的后端 RAG 索引，避免误删其他模式历史
    old_session_id = st.session_state.mode_sessions[mode]["session_id"]
    clear_indexed_document(old_session_id)

    # 只重置当前模式会话
    st.session_state.mode_sessions[mode] = {
        "session_id": str(uuid4()),
        "messages": []
    }

    # 只清空当前模式的前端索引状态缓存
    st.session_state.rag_index_state.pop(mode, None)
    # 清空当前模式聊天时，同步更新本地历史文件
    save_mode_sessions(st.session_state.mode_sessions)

    st.rerun()

# -----------------------------
# 统一输入入口
# 使用 st.chat_input 同时支持:
# 1. 纯文本输入
# 2. 文本 + 文件附件
# 3. 仅上传文件
# -----------------------------
chat_submission = st.chat_input(
    "请输入内容，或直接附加文件后发送...",
    accept_file=(mode in UPLOAD_ENABLED_MODES),
    file_type=CHAT_INPUT_FILE_TYPES if mode in UPLOAD_ENABLED_MODES else None,
    key=f"chat_input_{mode}"
)

submit_display_text = None   # 用于聊天区展示
submit_raw_text = None       # 真正发送给后端的 input_text
uploaded_file_name = None
uploaded_file_text = None

if chat_submission:
    # -----------------------------
    # 第一步：统一解析 chat_input 返回值
    # 说明：
    # - accept_file=True 时，chat_input 返回 dict-like 对象
    # - 包含 text 和 files
    # - 非上传模式下，仍然是普通字符串
    # -----------------------------
    if mode in UPLOAD_ENABLED_MODES:
        user_text = (chat_submission.text or "").strip()
        uploaded_files = chat_submission["files"]
    else:
        user_text = str(chat_submission).strip()
        uploaded_files = []

    uploaded_file = uploaded_files[0] if uploaded_files else None

    # -----------------------------
    # 第二步：如果附加了文件，先提取文本
    # -----------------------------
    if uploaded_file is not None:
        uploaded_file_name = uploaded_file.name
        uploaded_file_text, uploaded_file_error = extract_text_from_uploaded_file(uploaded_file)

        if uploaded_file_error:
            st.error(uploaded_file_error)
            # 立刻停止本次 Streamlit 脚本的继续执行
            st.stop()

    # 如果用户既没输入文字，也没附加文件，则不继续处理
    if not user_text and uploaded_file is None:
        st.stop()

    # -----------------------------
    # 第三步：构造展示文本和实际提交文本
    # -----------------------------
    if uploaded_file_text:
        submit_display_text = build_user_display_text(
            user_text=user_text,
            uploaded_file_name=uploaded_file_name
        )

        # 开启 RAG: 用户输入作为 query, 文档通过索引供后端检索
        if use_rag and mode in RAG_ENABLED_MODES:
            submit_raw_text = user_text or DEFAULT_FILE_MODE_PROMPTS[mode]
        else:
            # 不启用 RAG: 沿用“全文直接处理”的方式
            submit_raw_text = build_non_rag_input_text(
                user_text=user_text,
                uploaded_file_text=uploaded_file_text
            )
    else:
        # 没有文件时，沿用普通文本输入逻辑
        submit_display_text = user_text
        submit_raw_text = user_text

    # -----------------------------
    # 第四步：如果当前附加了文件并启用 RAG, 则先判断是否需要索引
    # -----------------------------
    if uploaded_file_text and use_rag and mode in RAG_ENABLED_MODES:
        text_fingerprint = build_text_fingerprint(uploaded_file_text)
        current_index_state = st.session_state.rag_index_state.get(mode)

        need_reindex = (
            not current_index_state
            or current_index_state.get("session_id") != current_session_id
            or current_index_state.get("text_fingerprint") != text_fingerprint
        )

        if need_reindex:
            # 前端告诉后端，进行索引文档操作
            success, message = index_uploaded_document(
                session_id=current_session_id,
                file_name=uploaded_file_name,
                document_text=uploaded_file_text
            )

            if not success:
                st.error(message)
                st.stop()

            st.success(message)

            st.session_state.rag_index_state[mode] = {
                "session_id": current_session_id,
                "file_name": uploaded_file_name,
                "text_fingerprint": text_fingerprint
            }

    # -----------------------------
    # 第五步: 展示并写入用户消息
    # -----------------------------
    with st.chat_message("user"):
        st.write(submit_display_text)

    current_messages.append({
        "role": "user",
        "content": submit_display_text,
        "raw_content": submit_raw_text
    })
    # 用户发送消息后立即保存历史
    save_mode_sessions(st.session_state.mode_sessions)

    # -----------------------------
    # 第六步: 根据模式决定调用哪个接口
    # -----------------------------
    task_type = MODE_TO_TASK_TYPE[mode]
    is_workflow = task_type == "workflow"

    # -----------------------------
    # 第七步: 构造符合 ChatRequest 的请求体并发送
    # -----------------------------
    payload = {
        "session_id": current_session_id,
        "task_type": task_type,
        "input_text": submit_raw_text,
        "persona": mode,
        "history": build_history_for_api(current_messages[:-1]), # 除了最后一个，前面的都要。current_messages[:-1]含义：当前这条刚追加的用户消息不要算进历史，因为它会单独作为本次的 input_text
        "user_options": {},
        "use_rag": use_rag,
        "rag_top_k": rag_top_k
    }

    # 发送流式请求
    response = post_stream_request(payload, is_workflow)

    # 请求失败直接报错
    if response.status_code != 200:
        st.error(f"请求失败: {response.text}")
    else:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("思考中... 🤔")

            # 用于聊天模式的完整文本
            full_response = ""
            # 用于工作流模式的分步骤结果
            workflow_blocks: dict[str, str] = {}
            # 标记是否收到第一条有效事件，用来清理“思考中”
            first_event_received = False

            # 逐行解析 SSE 事件流
            for event in iter_sse_events(response):
                event_type = event.get("event_type")
                step_name = event.get("step_name")
                content = event.get("content", "")
                error_message = event.get("error_message")

                # 第一次真正收到返回内容时，把‘思考中’提示移除，并标记后面不要再重复处理。
                if not first_event_received:
                    placeholder.empty()
                    first_event_received = True

                # 工作流开始 / 步骤开始：可选择显示状态，不强制写入最终结果
                if event_type in {"workflow_start", "step_start"}:
                    if is_workflow and step_name:
                        current_markdown = format_workflow_blocks(workflow_blocks)
                        if current_markdown:
                            placeholder.markdown(current_markdown)

                # 增量事件：按模式分别处理
                elif event_type == "delta":
                    if is_workflow:
                        if step_name:
                            # 如果 workflow_blocks 里还没有 step_name 这个 key，就先给它一个空字符串。如：{}会变成{"summary": ""}
                            workflow_blocks.setdefault(step_name, "")
                            # 把这次新来的内容，拼接到对应步骤后面
                            workflow_blocks[step_name] += content

                        placeholder.markdown(format_workflow_blocks(workflow_blocks) + "\n\n▌")
                    else:
                        full_response += content
                        placeholder.markdown(full_response + "▌")
                        # 让流式输出的视觉节奏更自然一点
                        time.sleep(0.01)

                # 步骤完成事件：用于工作流模式的最终分步内容落盘
                elif event_type == "step_complete":
                    # 只有确定这条事件确实属于某个步骤，才去写入对应步骤的数据。避免出现：workflow_blocks[None]
                    if step_name:
                        workflow_blocks[step_name] = content
                        placeholder.markdown(format_workflow_blocks(workflow_blocks))

                # 最终完成事件
                elif event_type == "final":
                    if is_workflow:
                        # 把当前已经积累好的 workflow_blocks 最终渲染一次
                        placeholder.markdown(format_workflow_blocks(workflow_blocks))
                    else:
                        # 如果前面没累计到内容，但 final 给了完整结果，那就拿 final.content 兜底
                        if not full_response and content:
                            full_response = content
                        placeholder.markdown(full_response)

                # 错误事件
                elif event_type == "error":
                    st.error(error_message or "请求失败")
                    break

            # 生成最终写入聊天记录的 assistant 内容（仅写入当前模式）
            if is_workflow:
                final_display_text = format_workflow_blocks(workflow_blocks)
            else:
                final_display_text = full_response

            # 当前轮结果操作区，在新结果生成后支持复制和导出
            if final_display_text.strip():
                render_result_actions(
                    result_text=final_display_text,
                    mode_name=mode,
                    widget_key_suffix="latest_result"
                )

                if is_workflow and workflow_blocks:
                    # 插入一个很小的空白间距。unsafe_allow_html=True表示：允许 Streamlit 按 HTML 来渲染这段字符串
                    st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)

                    render_workflow_step_copy_actions(
                        workflow_blocks=workflow_blocks,
                        widget_key_suffix="latest_steps"
                    )

                # 防止空内容写入历史
                assistant_message = {
                    "role": "assistant",
                    "content": final_display_text
                }

                # workflow 模式下，把分步结果一并保存到消息里，这样历史消息也能继续支持“分步复制”
                if is_workflow and workflow_blocks:
                    # 为什么用.copy()？因为 workflow_blocks 是一个字典，可变。.copy() 是复制一份，避免后面原字典变化时，把历史消息里的结果也带着改掉。
                    assistant_message["workflow_blocks"] = workflow_blocks.copy()

                current_messages.append(assistant_message)
                # 助手回复完成后再次保存历史
                save_mode_sessions(st.session_state.mode_sessions)
