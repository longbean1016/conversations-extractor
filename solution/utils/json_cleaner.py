"""JSON 清洗工具：处理 LLM 返回的各种格式问题。"""


def clean_json_response(raw: str) -> str:
    """清洗 LLM 返回的文本，提取纯 JSON。

    处理常见情况：
    - ```json ... ``` 包裹的 markdown 代码块
    - 前后的空白字符
    - 前后的解释文字（不常见，但防御性处理）

    Args:
        raw: LLM 原始返回文本

    Returns:
        清洗后的 JSON 字符串
    """
    raw = raw.strip()

    # 去除 markdown 代码块标记
    if raw.startswith("```"):
        first_newline = raw.find("\n")
        if first_newline != -1:
            raw = raw[first_newline + 1 :]
        if raw.rstrip().endswith("```"):
            raw = raw.rstrip()[: raw.rstrip().rfind("```")]

    return raw.strip()
