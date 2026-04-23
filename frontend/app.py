import json
import time
from uuid import uuid4

import requests
import streamlit as st


# -----------------------------
# 页面基础配置
# -----------------------------
st.set_page_config(
    page_title="AI智能助手平台",
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
    "工作流分析": "workflow"
}

AVAILABLE_MODES = list(MODE_TO_TASK_TYPE.keys())

mode = st.sidebar.selectbox("选择功能", AVAILABLE_MODES)


# -----------------------------
# Session State 初始化
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())


# -----------------------------
# 工具函数：将前端消息历史转换为后端 schema 需要的 history 格式
# 只保留最近 N 轮，避免上下文过长
# -----------------------------
MAX_HISTORY_LENGTH = 6

def build_history_for_api(messaegs: list[dict], max_length: int = MAX_HISTORY_LENGTH) -> list[dict]:
    """
    将前端消息列表剪裁并转换为后端可直接接收的 history 结构。

    每条消息保留：
    - role
    - content
    """
    history = []
    recent_messages = messeages[-max_length:]

    for message in recent_messages:
        role = message.get("role")
        content = message.get("content", "")

        if role not in {"user", "assistant", "system"}:
            continue

        history.append({
            "role": role, "content": content
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
# 展示历史消息
# assistant 消息支持 markdown，便于工作流分段展示
# -----------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# -----------------------------
# 清空聊天按钮
# -----------------------------
if st.sidebar.button("清空聊天"):
    st.session_state.messages = []
    st.session_state.session_id = str(uuid4())
    st.rerun()


# -----------------------------
# 输入框
# -----------------------------
prompt = st.chat_input("请输入您要处理的内容...")

if prompt:
    # 1. 先展示并保存用户输入
    with st.chat_message("user"):
        st.write(prompt)

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # 2. 根据模式决定调用哪个接口
    is_workflow = mode == "工作流优化"
    url = "http://127.0.0.1:8000/workflow_stream" if is_workflow else "http://127.0.0.1:8000/chat_stream"

    # 3. 构造符合 ChatRequest 的请求体
    payload = {
        "session_id": st.session_state.session_id,
        "task_type": MODE_TO_TASK_TYPE[mode],
        "input_text": prompt,
        "persona": mode,
        "history": build_history_for_api(st.session_state.messaegs[:-1]),
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

            # 标记是否收到第一条有效事件，用来清理”思考中“
            first_event_received = False

            # 6. 逐行解析 SSE 事件流
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue

                raw_text = raw_line.decode("utf-8").strip()

                # SSE 标准格式: data: {...}
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

                # 工作流开始 / 步骤开始: 可选择显示状态, 不强制写入最终结果
                if event_type in {"workflow_start", "step_start"}:
                    if is_workflow and step_name:
                        current_markdown = format_workflow_blocks(workflow_blocks)
                        if current_markdown:
                            placeholder.markdown(current_markdown)

                # 增量事件: 按模式分别处理
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

                # 步骤完成事件: 用于工作流模式的最终分步内容落盘
                elif event_type == "step_complete":
                    if step_name:
                        workflow_blocks[step_name] = content
                        placeholder.markdown(format_workflow_blocks(workflow_blocks))

                # 最终完成事件
                elif event_type == "final":
                    if is_workflow:
                        placeholder.markdown(format_workflow_blocks(workflow_blocks))
                    else:
                        # 聊天模式下, final.content 可能是完整文本; 如果前面 delta 已完整累计, 则无需重复追加
                        if not full_response and content:
                            full_response = content
                        placeholder.markdown(full_response)

                # 错误事件
                elif event_type == "error":
                    st.error(error_message or "请求失败")
                    break

            # 7. 生成最终写入聊天记录的 assistant 内容
            if is_workflow:
                final_display_text = format_workflow_blocks(workflow_blocks)
            else:
                final_display_text = full_response

            # 防止空内容写入历史
            if final_display_text.strip():
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": final_display_text
                })