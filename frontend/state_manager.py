import json
import time
from pathlib import Path
from uuid import uuid4


# 构造一个本地文件路径，指向：.../data/chat_history.json
HISTORY_FILE = Path(__file__).resolve().parents[1] / "data" / "chat_history.json"
# 当前历史文件的数据结构版本是 1
HISTORY_VERSION = 1
MAX_HISTORY_LENGTH = 6


def create_mode_sessions(mode_names: list[str]) -> dict:
    """
    为所有模式初始化独立会话。
    """
    return {
        mode_name: {
            "session_id": str(uuid4()),
            "messages": []
        }
        for mode_name in mode_names
    }


def normalize_messages(messages: list) -> list[dict]:
    """
    清理本地历史中的消息结构，避免坏数据影响页面渲染。
    """
    # 创建一个空列表，用来存放清洗后的消息
    normalized_messages = []

    for message in messages:
        # 如果这条消息不是字典，就跳过
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        content = message.get("content")

        if role not in {"user", "assistant", "system"} or not isinstance(content, str):
            continue

        # 先构造一条“最基础的干净消息”
        normalized_message = {
            "role": role,
            "content": content
        }

        # 如果这条消息里有 raw_content，并且它是字符串，就保留下来
        raw_content = message.get("raw_content")
        if isinstance(raw_content, str):
            normalized_message["raw_content"] = raw_content

        # 如果这条消息里带了 workflow 的分步结果，并且它是字典，就进一步清洗
        workflow_blocks = message.get("workflow_blocks")
        if isinstance(workflow_blocks, dict):
            normalized_message["workflow_blocks"] = {
                key: value
                for key, value in workflow_blocks.items()
                if isinstance(key, str) and isinstance(value, str)
            }

        normalized_messages.append(normalized_message)

    return normalized_messages


def load_mode_sessions(mode_names: list[str]) -> dict:
    """
    从本地 JSON 文件恢复各模式的会话历史；如果文件不存在、损坏或格式不对，就返回默认空会话。
    """
    # 生成一份默认会话。因为后面如果本地文件有问题，就直接返回这份默认值，不会影响页面启动。
    default_sessions = create_mode_sessions(mode_names)

    # 如果历史文件不存在，直接返回默认空会话。
    if not HISTORY_FILE.exists():
        return default_sessions

    try:
        # 读取历史文件内容，把 JSON 文本解析成 Python 数据。
        payload = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # 如果文件读失败、JSON格式损坏，直接返回默认空会话。避免因为本地历史文件坏了，整个页面打不开。
        return default_sessions

    saved_sessions = payload.get("mode_sessions", {})
    if not isinstance(saved_sessions, dict):
        return default_sessions

    # 遍历当前支持的每个模式
    for mode_name in mode_names:
        # 取出这个模式对应的历史会话
        saved_session = saved_sessions.get(mode_name)
        # 如果不是字典，就跳过这个模式。
        if not isinstance(saved_session, dict):
            continue

        session_id = saved_session.get("session_id")
        messages = saved_session.get("messages", [])

        # 把当前模式的默认会话，替换成”本地恢复后的会话“
        default_sessions[mode_name] = {
            "session_id": str(session_id) if session_id else str(uuid4()),
            "messages": normalize_messages(messages if isinstance(messages, list) else [])
        }

    return default_sessions


def save_mode_sessions(mode_sessions: dict) -> None:
    """
    把当前所有模式的会话历史保存到本地 JSON 文件。
    """
    try:
        # 如果历史文件所在目录不存在，则自动创建目录，避免写文件时报错
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(
            # 把 Python 字典转成 JSON 字符串
            json.dumps(
                {
                    "version": HISTORY_VERSION,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), # format time as string，把时间格式化成字符串
                    "mode_sessions": mode_sessions
                },
                ensure_ascii=False, # 允许中文正常保存，而不是变成 \u4f60\u597d
                indent=2 # 让 JSON 更好读，有缩进格式
            ),
            encoding="utf-8"
        )
    except OSError:
        # 本地历史保存失败不应阻断主流程，刷新后无法恢复即可由用户重新发起。
        pass


def ensure_mode_sessions(mode_sessions: dict, mode_names: list[str]) -> dict:
    """
    确保所有当前支持的模式都有会话容器。
    """
    for mode_name in mode_names:
        if mode_name not in mode_sessions:
            mode_sessions[mode_name] = {
                "session_id": str(uuid4()),
                "messages": []
            }

    return mode_sessions


def build_history_for_api(messages: list[dict], max_length: int = MAX_HISTORY_LENGTH) -> list[dict]:
    """
    将前端消息列表裁剪并转换为后端可直接接收的 history 结构。只保留最近 N 轮，避免上下文过长。

    每条消息保留：
    - role
    - content
    说明:
    - 普通文本输入直接使用 content
    - 文件上传消息优先使用 raw_content, 保证历史上下文仍热是完整文本
    """
    history = []
    # 只取最后 max_length 条消息
    recent_messages = messages[-max_length:]

    for message in recent_messages:
        role = message.get("role")
        # 核心目的： 上传文件时，前端显示用 content，后端历史用 raw_content
        content = message.get("raw_content", message.get("content", ""))

        # 若角色不合法，就跳过这条消息
        if role not in {"user", "assistant", "system"}:
            continue

        history.append({
            "role": role,
            "content": content
        })

    return history
