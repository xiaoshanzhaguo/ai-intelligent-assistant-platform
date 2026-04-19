import streamlit as st
import os
from openai import OpenAI

from dotenv import load_dotenv

import time

# 加载环境变量
load_dotenv()

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

# 系统提示词
system_prompt= "你是一名聪明智慧的AI智能助手，可以帮助用户处理多种问题。"

# 初始化聊天信息
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 展示聊天信息
for message in st.session_state.messages:
    # 使用st.chat_message上下文管理器来正确显示消息
    # with st.chat_message(message["role"]):
    #     st.write(message["content"])
    st.chat_message(message["role"]).write(message["content"])

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
    with st.spinner("数据加载中，请稍后"):  # type: ignore
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                *st.session_state.messages # 列表中的解包
            ],
            stream=True
        )

    # 输出大模型返回的结果(流式输出的解析方式)
    response_message = st.empty() # 创建一个空的组件，用于展示大模型返回的结果
    full_response = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            response_message.chat_message("assistant").write(full_response)

    # 保存大模型返回的结果
    st.session_state.messages.append({"role": "assistant", "content": full_response})