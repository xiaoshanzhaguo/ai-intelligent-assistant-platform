from backend.prompt.prompt_templates import ROLE_PROMPTS
from backend.prompt.base_prompt import BASE_PROMPT

ROLE_MAP = {
    "聊天": "assistant",
    "总结": "assistant",
    "翻译": "assistant",
    "改写": "assistant"
}

def build_system_prompt(role, nick_name="", nature="", custom_prompt=""):
    role_key = ROLE_MAP.get(role, "assistant")

    role_prompt_template = ROLE_PROMPTS.get(role_key, ROLE_PROMPTS["assistant"])

    # 填充变量
    role_prompt = role_prompt_template.format(
        nick_name=nick_name,
        nature=nature,
    )

    final_prompt = f"""
        {BASE_PROMPT}
        【当前角色设定】
        {role_prompt}
        【用户自定义补充】
        {custom_prompt}
        请严格按照以上设定进行回复
    """

    return final_prompt