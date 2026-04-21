from openai import OpenAI
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 模型调用。好处：后面换模型不用动别的代码
def get_client():
    return OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url=os.getenv("BASE_URL")
)