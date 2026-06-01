import json
import time
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components


STEP_TITLE_MAP = {
    "summary": "🧠 内容总结",
    "analysis": "🔍 问题分析",
    "suggestion": "✨ 优化建议"
}


def format_workflow_blocks(workflow_blocks: dict[str, str]) -> str:
    """
    将工作流分步骤结果格式化为 Markdown 展示。
    """
    formatted_parts = []

    for step_name in ["summary", "analysis", "suggestion"]:
        content = workflow_blocks.get(step_name, "").strip()
        if not content:
            continue

        title = STEP_TITLE_MAP.get(step_name, step_name)
        formatted_parts.append(f"### {title}\n\n{content}\n")

    return "\n\n".join(formatted_parts)


def build_markdown_filename(mode_name: str) -> str:
    """
    生成 Markdown 导出文件名。
    """
    # 生成当前时间字符串，格式为：年月日_时分秒。如：20260601_153045
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_mode_name = mode_name.replace(" ", "_")
    return f"{safe_mode_name}_result_{timestamp}.md"


def build_markdown_content(mode_name: str, result_text: str) -> str:
    """
    将结果包装成更完整的 Markdown 文本，便于导出保存。
    """
    export_time = time.strftime("%Y-%m-%d %H:%M:%S")
    return (
        "# AI 内容分析与创作助手导出结果\n\n"
        f"- 模式：{mode_name}\n"
        f"- 导出时间：{export_time}\n\n"
        "---\n\n"
        f"{result_text.strip()}\n"
    )


def render_copy_button(text: str, label: str, button_id_suffix: str) -> None:
    """
    渲染一个复制按钮，用于将指定文本复制到剪贴板。通过内嵌 HTML + JS 将结果复制到系统剪贴板。

    :param text: 需要复制的文本内容
    :param label: 按钮上显示的文字
    :param button_id_suffix: 用于生成唯一按钮 ID，避免多个按钮冲突
    :return: None
    """
    button_id = f"copy_btn_{button_id_suffix}_{uuid4().hex}"

    components.html(
        f"""
        <html>
        <head>
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    overflow: hidden;
                }}

                .copy-btn {{
                    width: 100%;
                    height: 38px;
                    border: 1px solid #d0d7de;
                    border-radius: 0.5rem;
                    background: white;
                    color: #111827;
                    font-size: 0.95rem;
                    cursor: pointer;
                    box-sizing: border-box;
                }}

                .copy-btn:hover {{
                    background: #f9fafb;
                }}
            </style>
        </head>
        <body>
            <button id="{button_id}" class="copy-btn">{label}</button>

            <script>
                const btn = document.getElementById("{button_id}");
                btn.onclick = async () => {{
                    try {{
                        await navigator.clipboard.writeText({json.dumps(text)});
                        const oldText = btn.innerText;
                        btn.innerText = "已复制";
                        setTimeout(() => btn.innerText = oldText, 1500);
                    }} catch (err) {{
                        const oldText = btn.innerText;
                        btn.innerText = "复制失败";
                        setTimeout(() => btn.innerText = oldText, 1500);
                    }}
                }};
            </script>
        </body>
        </html>
        """,
        height=40,
    )


def render_result_actions(result_text: str, mode_name: str, widget_key_suffix: str) -> None:
    """
    为 assistant 结果渲染操作按钮：
    1. 复制当前结果
    2. 导出 Markdown
    """
    if not result_text.strip():
        return

    markdown_content = build_markdown_content(mode_name, result_text)
    file_name = build_markdown_filename(mode_name)

    # 创建两列布局
    col1, col2 = st.columns(2, gap="small")

    # with col1: 表示下面这一小段组件渲染到左边那一列里。
    with col1:
        # 在左列渲染复制按钮
        render_copy_button(
            text=result_text,
            label="复制当前结果",
            button_id_suffix=widget_key_suffix
        )

    with col2:
        st.download_button(
            label="导出 Markdown",
            data=markdown_content.encode("utf-8-sig"),  # 下载的内容本体，带 BOM 便于 Windows 编辑器识别中文
            file_name=file_name,
            mime="text/markdown; charset=utf-8",  # 告诉浏览器这是 UTF-8 Markdown 文本文件
            key=f"download_md_{widget_key_suffix}",  # 确保这个按钮在 Streamlit 里是唯一的
            on_click="ignore",  # 点击后忽略默认点击行为带来的额外处理，只保留当前组件本身想做的事情
            use_container_width=True,  # 按钮宽度撑满这一列
        )


def render_workflow_step_copy_actions(workflow_blocks: dict[str, str], widget_key_suffix: str) -> None:
    """
    为 workflow 结果渲染“分步复制”按钮。
    默认折叠，避免界面过于拥挤。
    :param workflow_blocks: workflow 三个步骤的结果字典
    :param widget_key_suffix: 唯一后缀，防止按钮 key 冲突
    """
    # 如果没有 workflow 数据，就不用渲染任何东西
    if not workflow_blocks:
        return

    # 创建一个可折叠区域，标题叫“分步复制”，默认收起
    with st.expander("分步复制", expanded=False):
        # 创建三列布局，用来放三个按钮
        col1, col2, col3 = st.columns(3, gap="small")

        with col1:
            summary_text = workflow_blocks.get("summary", "").strip()
            # 如果这一步确实有内容，才显示按钮
            if summary_text:
                render_copy_button(
                    text=summary_text,
                    label="复制总结",
                    button_id_suffix=f"{widget_key_suffix}_summary"
                )

        with col2:
            analysis_text = workflow_blocks.get("analysis", "").strip()
            if analysis_text:
                render_copy_button(
                    text=analysis_text,
                    label="复制问题",
                    button_id_suffix=f"{widget_key_suffix}_analysis"
                )

        with col3:
            suggestion_text = workflow_blocks.get("suggestion", "").strip()
            if suggestion_text:
                render_copy_button(
                    text=suggestion_text,
                    label="复制建议",
                    button_id_suffix=f"{widget_key_suffix}_suggestion"
                )
