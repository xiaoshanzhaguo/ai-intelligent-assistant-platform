# 多步骤工作流
def run_workflow_stream(user_input, client):
    steps = [
        {"name": "总结", "prompt": f"请总结一下内容：\n{user_input}"},
        {"name": "问题分析", "prompt": f"请分析以下内容存在的问题：\n{user_input}"},
        {"name": "优化建议", "prompt": f"请给出优化建议：\n{user_input}"}
    ]

    for step in steps:
        # 先告诉前端：当前步骤
        yield  f"\n\n【{step['name']}】"

        # 调用AI（流式）
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": step["prompt"]}],
            stream=True # 关键
        )

        # 一点点返回内容
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content