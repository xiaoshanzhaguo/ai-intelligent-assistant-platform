import os

from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env 环境变量
load_dotenv()


def get_client() -> OpenAI:
    """
    创建并返回统一的大模型客户端。

    通过环境变量读取 API Key 和 Base URL,
    便于后续切换不同模型服务商时，避免修改业务层代码。
    """
    api_key=os.environ.get("DEEPSEEK_API_KEY")
    base_url = os.getenv("BASE_URL")

    if not api_key:
        raise ValueError("未检测到 DEEPSEEK_API_KEY，请检查 .env 配置。")

    if not base_url:
        raise ValueError("未检测到 BASE_URL，请检查 .env 配置。")

    return OpenAI(
        api_key=api_key,
        base_url=base_url
)