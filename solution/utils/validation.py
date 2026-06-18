"""结果校验：检查提取结果是否符合 Schema 定义。"""

from config.schema import get_required_fields, get_field_enums


def validate_result(result: dict) -> list[str]:
    """校验单条提取结果，返回问题列表。

    Args:
        result: 提取结果 dict

    Returns:
        问题描述列表，空列表表示校验通过
    """
    issues = []

    # 1. 检查必填字段
    for field in get_required_fields():
        if field not in result or result[field] is None:
            issues.append(f"缺少字段: {field}")

    # 2. 检查枚举字段
    field_enums = get_field_enums()
    for field_name, valid_values in field_enums.items():
        value = result.get(field_name)
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                if item not in valid_values:
                    issues.append(f"{field_name} 元素越界: {item}")
        else:
            if value not in valid_values:
                issues.append(f"{field_name} 值越界: {value}")

    # 3. 检查 channel（非函数 enum，但约定为在线/电话）
    channel = result.get("channel", "")
    if channel and channel not in ("在线", "电话"):
        issues.append(f"channel 值越界: {channel}")

    return issues
