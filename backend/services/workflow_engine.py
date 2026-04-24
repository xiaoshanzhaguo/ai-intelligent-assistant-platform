import json

from fastapi.responses import StreamingResponse

from backend.prompt.prompt_builder import build_system_prompt
from backend.schema.chat_schema import ChatRequest, StreamEvent
from backend.utils.stream_helper import to_sse


def run_workflow_stream(request: ChatRequest, client) -> StreamingResponse:
    """
    工作流流式服务。

    将多步骤内容分析流程封装为 SSE 事件流返回给前端，
    支持工作流开始、步骤开始、增量输出、步骤完成、最终完成和错误事件。
    """

    def generate():
        """
        生成工作流事件流。

        流程：
        1. 构造 system prompt
        2. 定义多步骤工作流
        3. 逐步调用模型并流式输出
        4. 每个步骤结束后发送 step_complete事件
        5. 所有步骤结束后发送 final 事件
        6. 若发生异常，则发送 error 事件
        """
        final_result = {}

        try:
            # 根据当前助手人设或内容风格生成系统提示词
            system_prompt = build_system_prompt(request.persona)

            # 通知前端：整个工作流开始
            yield to_sse(
                StreamEvent(
                    event_type="workflow_start",
                    session_id=request.session_id,
                    task_type=request.task_type,
                    content="工作流已开始"
                )
            )

            # 定义工作流步骤
            steps = [
                {
                    "name": "summary",
                    "prompt": f"请总结以下内容的核心观点与重点信息：\n{request.input_text}"
                },
                {
                    "name": "analysis",
                    "prompt": f"""
                        请仅分析以下内容中已经明确出现的问题或不足。
                        要求：
                        1. 不补充输入中未明确出现的新问题。
                        2. 不给建议。
                        3. 输出简洁、结构化。
                        
                        内容如下：
                        {request.input_text}
                    """.strip()
                },
                {
                    "name": "suggestion",
                    "prompt": f"""
                        请仅基于以下内容中已经明确出现的问题，给出 3 条最值得优先执行的优化建议。
                        要求：
                        1. 只给建议，不重复总结和问题分析。
                        2. 每条建议必须直接对应输入中已出现的问题。
                        3. 不补充新技术、新框架、新工具、新平台、新指标。
                        4. 输出简洁、可执行、按重要性排序。
                        
                        内容如下：
                        {request.input_text}
                    """.strip()
                }
            ]

            # 依次执行每个工作流步骤
            for step in steps:
                step_name = step["name"]
                step_text = ""

                # 通知前端：当前步骤开始执行
                yield to_sse(
                    StreamEvent(
                        event_type="step_start",
                        session_id=request.session_id,
                        task_type=request.task_type,
                        step_name=step_name,
                        content=f"{step_name} 步骤开始"
                    )
                )

                # 组装本步骤的消息上下文
                messages = [{"role": "system", "content": system_prompt}]

                # 如果存在历史消息，则拼接到上下文中
                if request.history:
                    messages.extend([msg.model_dump() for msg in request.history])

                # 加入当前步骤提示词
                messages.append({"role": "user", "content": step["prompt"]})

                # 调用模型接口，开启当前步骤的流式输出
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    stream=True
                )

                # 持续读取当前步骤的增量输出
                for chunk in response:
                    delta = chunk.choices[0].delta.content

                    if not delta:
                        continue

                    step_text += delta

                    # 向前端发送当前步骤的增量内容
                    yield to_sse(
                        StreamEvent(
                            event_type="delta",
                            session_id=request.session_id,
                            task_type=request.task_type,
                            step_name=step_name,
                            content=delta
                        )
                    )

                # 保存当前步骤的完整结果
                final_result[step_name] = step_text

                # 通知前端：当前步骤已经完成
                yield to_sse(
                    StreamEvent(
                        event_type="step_complete",
                        session_id=request.session_id,
                        task_type=request.task_type,
                        step_name=step_name,
                        content=step_text,
                    )
                )

            # 所有步骤执行完成后，发送最终事件
            yield to_sse(
                StreamEvent(
                    event_type="final",
                    session_id=request.session_id,
                    task_type=request.task_type,
                    content=json.dumps(final_result, ensure_ascii=False),
                    is_final=True
                )
            )

        except Exception as e:
            # 若执行过程中发生异常，则返回结构化错误事件
            yield to_sse(
                StreamEvent(
                    event_type="error",
                    session_id=request.session_id,
                    task_type=request.task_type,
                    error_message=str(e),
                    is_final=True
                )
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
