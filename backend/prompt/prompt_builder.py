from backend.prompt.base_prompt import BASE_PROMPT
from backend.prompt.prompt_templates import PERSONA_PROMPTS

def build_system_prompt(persona: str = "default", custom_prompt: str = "") -> str:
    """
    根据 persona 构造系统提示词

    :param persona: 当前助手人设或模式名称, 例如”内容分析“”结构优化“等
    :param custom_prompt: 用户额外补充的提示词，默认为空
    :return: 拼接完成后的提示词字符串
    """
    persona_prompt = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["default"])

    final_prompt = f"""
         {BASE_PROMPT}
         
         【当前人设 / 模式设定】
         {persona_prompt}
         
         【用户自定义补充】
         {custom_prompt if custom_prompt else "无"}
         
         请严格按照以上设定完成回复。
    """.strip()

    return final_prompt