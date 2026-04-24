import json
import time
from uuid import uuid4

import requests
import streamlit as st
import streamlit.components.v1 as components


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

AVAILABLE_MODES = list(MODE_TO_TASK_TYPE.keys())
mode = st.sidebar.selectbox("选择功能", AVAILABLE_MODES)


# -----------------------------
# 工具函数：创建所有模式的会话容器
# 每个模式都维护自己的 session_id 和 messages
# -----------------------------
def create_mode_sessions(mode_names: list[str]) -> dict:
    """
    为所有模式初始化独立会话。

    返回格式：
    {
        "内容分析": {
            "session_id": "...",
            "messages": []
        },
        ...
    }
    """
    return {
        mode_name: {
            "session_id": str(uuid4()),
            "messages": []
        }
        for mode_name in mode_names
    }


# -----------------------------
# Session State 初始化
# 如果不存在，或被清空为 {}，则重新初始化
# -----------------------------
if "mode_sessions" not in st.session_state or not st.session_state.mode_sessions:
    st.session_state.mode_sessions = create_mode_sessions(AVAILABLE_MODES)

# 当前模式对应的会话状态
current_session = st.session_state.mode_sessions[mode]
current_session_id = current_session["session_id"]
current_messages = current_session["messages"]


# -----------------------------
# 工具函数：将前端消息历史转换为后端 schema 需要的 history 格式
# 只保留最近 N 轮，避免上下文过长
# -----------------------------
MAX_HISTORY_LENGTH = 6


def build_history_for_api(messages: list[dict], max_length: int = MAX_HISTORY_LENGTH) -> list[dict]:
    """
    将前端消息列表裁剪并转换为后端可直接接收的 history 结构。

    每条消息保留：
    - role
    - content
    """
    history = []
    recent_messages = messages[-max_length:]

    for message in recent_messages:
        role = message.get("role")
        content = message.get("content", "")

        if role not in {"user", "assistant", "system"}:
            continue

        history.append({
            "role": role,
            "content": content
        })

    return history


# -----------------------------
# 工具函数：格式化工作流步骤输出
# 将 step_name 转成更友好的中文标题
# -----------------------------
STEP_TITLE_MAP = {
    "summary": "🧠 内容总结",
    "analysis": "🔍 问题分析",
    "suggestion": "✨ 优化建议"
}


def format_workflow_blocks(workflow_blocks: dict[str, str]) -> str:
    """
    将工作流分步骤结果格式化为 Markdown 展示。
    """
    formatted_parts = []

    for step_name in ["summary", "analysis", "suggestion"]:
        content = workflow_blocks.get(step_name, "").strip()
        if not content:
            continue

        title = STEP_TITLE_MAP.get(step_name, step_name)
        formatted_parts.append(f"### {title}\n\n{content}\n")

    return "\n\n".join(formatted_parts)


# -----------------------------
# 工具函数：生成 Markdown 文件名
# mode_name 用于区分不同模式导出的结果
# -----------------------------
def build_markdown_filename(mode_name: str) -> str:
    """
    生成 Markdown 导出文件名。
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_mode_name = mode_name.replace(" ", "_")
    return f"{safe_mode_name}_result_{timestamp}.md"


# -----------------------------
# 工具函数：构造 Markdown 导出内容
# 为导出的文件增加标题和模式信息
# -----------------------------
def build_markdown_content(mode_name: str, result_text: str) -> str:
    """
    将结果包装成更完整的 Markdown 文本，便于导出保存。
    """
    export_time = time.strftime("%Y-%m-%d %H:%M:%S")
    return f"""# AI 内容分析与创作助手导出结果

- 模式：{mode_name}
- 导出时间：{export_time}

---

{result_text}
"""


# -----------------------------
# 工具函数：渲染复制按钮
# 通过内嵌 HTML + JS 将结果复制到系统剪贴板
# -----------------------------
def render_copy_button(text: str, button_id_suffix: str) -> None:
    """
    渲染一个复制按钮，用于将结果复制到剪贴板。
    """
    button_id = f"copy_btn_{button_id_suffix}_{uuid4().hex}"

    components.html(
        f"""
        <button id="{button_id}" style="
            width: 100%;
            padding: 0.45rem 0.75rem;
            border-radius: 0.5rem;
            border: 1px solid #d0d7de;
            background: white;
            cursor: pointer;
            font-size: 0.95rem;
        ">复制当前结果</button>

        <script>
        const btn = document.getElementById("{button_id}");
        btn.onclick = async () => {{
            try {{
                await navigator.clipboard.writeText({json.dumps(text)});
                const oldText = btn.innerText;
                btn.innerText = "已复制";
                setTimeout(() => btn.innerText = oldText, 1500);
            }} catch (err) {{
                btn.innerText = "复制失败";
                setTimeout(() => btn.innerText = "复制当前结果", 1500);
            }}
        }};
        </script>
        """,
        height=45,
    )


# -----------------------------
# 工具函数：渲染结果操作区
# 包括：
# 1. 复制当前结果
# 2. 导出 Markdown
# -----------------------------
def render_result_actions(result_text: str, mode_name: str, widget_key_suffix: str) -> None:
    """
    为 assistant 结果渲染操作按钮。
    """
    if not result_text.strip():
        return

    markdown_content = build_markdown_content(mode_name, result_text)
    file_name = build_markdown_filename(mode_name)

    col1, col2 = st.columns(2)

    with col1:
        render_copy_button(result_text, widget_key_suffix)

    with col2:
        st.download_button(
            label="导出 Markdown",
            data=markdown_content,
            file_name=file_name,
            mime="text/markdown",
            key=f"download_md_{widget_key_suffix}",
            use_container_width=True
        )


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
            render_result_actions(
                result_text=message["content"],
                mode_name=mode,
                widget_key_suffix=f"history_{idx}"
            )


# -----------------------------
# 会话控制按钮
# -----------------------------
if st.sidebar.button("新建当前模式聊天"):
    st.session_state.mode_sessions[mode] = {
        "session_id": str(uuid4()),
        "messages": []
    }
    st.rerun()

if st.sidebar.button("清空全部聊天"):
    st.session_state.mode_sessions = create_mode_sessions(AVAILABLE_MODES)
    st.rerun()


# -----------------------------
# 输入框
# -----------------------------
prompt = st.chat_input("请输入您要处理的内容...")

if prompt:
    # 1. 先展示并保存用户输入（仅写入当前模式）
    with st.chat_message("user"):
        st.write(prompt)

    current_messages.append({
        "role": "user",
        "content": prompt
    })

    # 2. 根据模式决定调用哪个接口
    is_workflow = mode == "工作流优化"
    url = "http://127.0.0.1:8000/workflow_stream" if is_workflow else "http://127.0.0.1:8000/chat_stream"

    # 3. 构造符合 ChatRequest 的请求体
    payload = {
        "session_id": current_session_id,
        "task_type": MODE_TO_TASK_TYPE[mode],
        "input_text": prompt,
        "persona": mode,
        "history": build_history_for_api(current_messages[:-1]),
        "user_options": {}
    }

    # 4. 发送流式请求
    response = requests.post(
        url,
        json=payload,
        stream=True,
        timeout=120
    )

    # 5. 请求失败直接报错
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

            # 6. 逐行解析 SSE 事件流
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue

                raw_text = raw_line.decode("utf-8").strip()

                # SSE 标准格式：data: {...}
                if not raw_text.startswith("data: "):
                    continue

                json_text = raw_text[6:]

                try:
                    event = json.loads(json_text)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("event_type")
                step_name = event.get("step_name")
                content = event.get("content", "")
                error_message = event.get("error_message")

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
                            workflow_blocks.setdefault(step_name, "")
                            workflow_blocks[step_name] += content

                        placeholder.markdown(format_workflow_blocks(workflow_blocks) + "\n\n▌")
                    else:
                        full_response += content
                        placeholder.markdown(full_response + "▌")
                        time.sleep(0.01)

                # 步骤完成事件：用于工作流模式的最终分步内容落盘
                elif event_type == "step_complete":
                    if step_name:
                        workflow_blocks[step_name] = content
                        placeholder.markdown(format_workflow_blocks(workflow_blocks))

                # 最终完成事件
                elif event_type == "final":
                    if is_workflow:
                        placeholder.markdown(format_workflow_blocks(workflow_blocks))
                    else:
                        # 聊天模式下，final.content 可能是完整文本；
                        # 如果前面 delta 已完整累计，则无需重复追加
                        if not full_response and content:
                            full_response = content
                        placeholder.markdown(full_response)

                # 错误事件
                elif event_type == "error":
                    st.error(error_message or "请求失败")
                    break

            # 7. 生成最终写入聊天记录的 assistant 内容（仅写入当前模式）
            if is_workflow:
                final_display_text = format_workflow_blocks(workflow_blocks)
            else:
                final_display_text = full_response

            # 8. 当前轮结果操作区
            # 在新结果刚生成时，立即支持复制和 Markdown 导出
            if final_display_text.strip():
                render_result_actions(
                    result_text=final_display_text,
                    mode_name=mode,
                    widget_key_suffix="latest_result"
                )

            # 9. 防止空内容写入历史
            if final_display_text.strip():
                current_messages.append({
                    "role": "assistant",
                    "content": final_display_text
                })