import requests
import streamlit as st
from openai import OpenAI
import os
import time
import random

# 配置页面的配置项
st.set_page_config(
    page_title="AI智能助手平台",
    page_icon="🤖",
    # 布局
    layout="wide",
    # 侧边栏状态
    initial_sidebar_state="expanded",
    menu_items={}
)

# 大标题
st.title("AI智能助手平台")

# 实现多模式功能
mode = st.sidebar.selectbox(
    "选择功能",
    ["聊天", "总结", "翻译", "改写"]
)

# 初始化聊天信息
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 展示聊天信息
for message in st.session_state.messages:
    # 使用st.chat_message上下文管理器来正确显示消息
    # with st.chat_message(message["role"]):
    #     st.write(message["content"])
    st.chat_message(message["role"]).write(message["content"])

# 上下文窗口裁剪，实现对话历史长度限制
MAX_HISTORY_LENGTH = 6
messages = st.session_state.messages[-MAX_HISTORY_LENGTH:]

# 加“清空聊天按钮”
if st.sidebar.button("清空聊天"):
    st.session_state.messages = []

# 创建与AI大模型交互的客户端对象
client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url=os.getenv("BASE_URL")
)

# 消息输入框
prompt = st.chat_input("请输入您要问的问题：")
if prompt:
    # 将用户输入的提示词保存到会话状态中
    with st.chat_message("user"):
        st.write(prompt)
    # 保存用户输入的提示词
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用AI，返回response，获取AI的回复
    response = requests.post(
        "http://127.0.0.1:8000/chat_stream",
        json={
            "message": prompt,
            "role": mode
        },
        stream=True
    )

    # 前端加一层保护, 进行错误处理
    if response.status_code != 200:
        st.error(f"请求失败: {response.text}")
    else:
        with st.chat_message("assistant"):  # type: ignore
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("思考中... 🤔")

            # 输出大模型返回的结果(流式输出的解析方式)
            # response_container = None
            # response_placeholder = None
            full_response = ""
            first_chunk = True

            for chunk in response.iter_lines():
                if chunk:
                    text = chunk.decode("utf-8")

                    if first_chunk:
                        thinking_placeholder.empty() # 清除掉"思考中"
                        first_chunk = False

                    # 逐词输出
                    for char in text:
                        full_response += char
                        # 显示内容 + 光标
                        thinking_placeholder.markdown(full_response + "▌")
                        # 1. 动态速度（前快后慢），并且设置随机微抖动（更自然）
                        base_speed = 0.005 if len(full_response) < 50 else 0.01
                        jitter = random.uniform(-0.002, 0.002)
                        # 2. 标点停顿（更像人）
                        if char in "，。！？":
                            time.sleep(0.05)
                        else:
                            time.sleep(max(0.001, base_speed + jitter))

            # 最后去掉光标, 最终渲染
            thinking_placeholder.markdown(full_response)

            # 保存大模型返回的结果
            st.session_state.messages.append({"role": "assistant", "content": full_response})