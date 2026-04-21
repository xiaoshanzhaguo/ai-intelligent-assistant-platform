# 将AI调用抽出来
from fastapi.responses import StreamingResponse
from backend.prompt.prompt_builder import build_system_prompt
from backend.schema.chat_schema import ChatRequest

# 核心逻辑
def chat_with_ai(request: ChatRequest, client):
    # 加try-catch, 让程序员能看到真实错误
    try:
        system_prompt = build_system_prompt(request.role)

        # response = client.chat.completions.create(
        #     model="deepseek-chat",
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         *req.messages
        #     ]
        # )
        #
        # return {
        #     "response": response.choices[0].message.content
        # }

        def generate():
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.message}
                ],
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content  # yield实现一点点吐

        return StreamingResponse(generate(), media_type="text/plain")  # StreamingResponse告诉前端这是流
    except Exception as e:
        print("报错：", str(e))
        return {"response": "后端出错了"}
