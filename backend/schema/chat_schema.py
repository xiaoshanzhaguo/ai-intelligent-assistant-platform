from pydantic import BaseModel, Field
from typing import Optional, Literal, TypeAlias, List, Dict, Any

MessageRole: TypeAlias = Literal["system", "user", "assistant"]
TaskType: TypeAlias = Literal["chat", "summary", "rewrite", "translate", "workflow"]
StreamEventType: TypeAlias = Literal[
    "workflow_start",   # 整个工作流开始
    "step_start",       # 某个步骤开始
    "delta",            # 生成一小段增量内容
    "step_complete",    # 某个步骤完成
    "final",            # 整个任务结束
    "error"             # 发生错误
]

class MessageItem(BaseModel):
    """单条消息模型。"""

    role: MessageRole  # 消息角色
    content: str  # 消息内容

class ChatRequest(BaseModel):
    """
    AI 内容任务请求体模型。

    用于描述一次完整的 AI 内容处理请求，
    包括当前输入、任务类型、历史上下文和扩展参数。
    """

    session_id: Optional[str] = None  # 会话 ID，用于区分不同对话
    task_type: TaskType = "chat"  # 当前任务类型
    input_text: str  # 用户本次输入内容
    persona: str = "default"   # 助手人设或内容风格标识
    history: List[MessageItem] = Field(default_factory=list)  # 历史消息列表
    user_options: Dict[str, Any] = Field(default_factory=dict)  # 扩展参数，如语气、长度、语言等

class StreamEvent(BaseModel):
    """
    流式事件模型。

    用于后端在流式输出过程中，向前端持续发送事件消息。
    前端可根据事件类型更新界面状态、拼接文本内容或处理异常。
    """

    event_type: StreamEventType  # 当前流式事件的类型
    session_id: Optional[str] = None  # 当前事件所属的会话ID
    task_type: Optional[TaskType] = None  # 当前任务类型
    step_name: Optional[str] = None  # 当前事件关联的步骤名称
    content: str = ""  # 当前事件携带的文本内容
    is_final: bool = False  # 是否为最后一条流式消息
    error_message: Optional[str] = None  # 错误信息，仅在 error 事件中使用