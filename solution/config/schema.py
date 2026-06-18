"""
提取 Schema 唯一定义源。

所有字段定义、枚举值、校验规则集中在此文件。
修改 Schema 只需改这里，其余模块自动跟随。
"""

from typing import Any

# ============================================================
# 枚举值定义
# ============================================================

VALID_CATEGORIES = {
    "商品质量",
    "退款退货",
    "物流配送",
    "优惠促销",
    "账号安全",
    "商品咨询",
    "功能建议",
    "其他",
}

VALID_SENTIMENTS = {"positive", "neutral", "negative", "angry"}

VALID_CHANNELS = {"在线", "电话"}

VALID_ATTENTION_FLAGS = {
    "舆情风险",
    "重复投诉",
    "长时间未解决",
    "用户流失",
    "服务事故",
}

# ============================================================
# 字段定义（14 字段）
# description 只写本字段特有的判断边界，通用规则见 System Prompt
# ============================================================

FIELD_DEFINITIONS: list[dict[str, Any]] = [
    # --- 基础信息 ---
    {
        "name": "conversation_id",
        "type": "string",
        "required": True,
        "description": "对话唯一标识，从输入中获取",
    },
    {
        "name": "channel",
        "type": "string",
        "enum": list(VALID_CHANNELS),
        "required": True,
        "description": "对话渠道",
    },
    {
        "name": "agent",
        "type": "string",
        "required": True,
        "description": "客服姓名",
    },
    # --- 问题描述 ---
    {
        "name": "summary",
        "type": "string",
        "required": True,
        "description": (
            "一句话摘要，不超过50字。"
            "格式：用户[核心诉求] + [处理结果]。"
            "多诉求时覆盖全部要点；空对话如实描述'用户未提出具体问题'"
        ),
    },
    {
        "name": "primary_category",
        "type": "string",
        "enum": list(VALID_CATEGORIES),
        "required": True,
        "description": (
            "主要问题分类，按问题根因选最匹配的一个。"
            "退款退货 与 商品质量 重叠时，优先商品质量（品质是根因）。"
            "投诉情绪不作为分类依据"
        ),
    },
    {
        "name": "secondary_categories",
        "type": "array",
        "items": {"type": "string", "enum": list(VALID_CATEGORIES)},
        "required": True,
        "description": "次要问题分类。单一问题为空数组，多诉求列出其余类别",
    },
    # --- 解决状态 ---
    {
        "name": "is_resolved",
        "type": "boolean",
        "required": True,
        "description": (
            "问题是否解决。"
            "true：给出明确方案且用户接受；纯咨询类固定为 true。"
            "false：用户放弃、转人工后无下文、信息不足、去别处购买。"
            "区分要点：'行吧/好吧'是接受(true)，'算了不看了/不用了'是放弃(false)"
        ),
    },
    {
        "name": "resolution",
        "type": "string",
        "required": True,
        "description": "解决方案简述，不超过30字。已解决：描述方案；未解决：说明原因",
    },
    {
        "name": "is_inquiry_only",
        "type": "boolean",
        "required": True,
        "description": (
            "是否为纯咨询。"
            "true：仅查询信息或提建议，无售后需求。"
            "false：涉及退款/退货/投诉等实际业务处理。"
            "有进行中售后订单的进度查询不算纯咨询"
        ),
    },
    # --- 情绪与风险 ---
    {
        "name": "user_sentiment",
        "type": "string",
        "enum": list(VALID_SENTIMENTS),
        "required": True,
        "description": (
            "用户整体情绪，看用词强度而非问题严重度。"
            "angry：辱骂词、3+个感叹号、明确投诉意图。"
            "negative：不满但克制。"
            "neutral：普通陈述。"
            "positive：主动感谢或称赞"
        ),
    },
    {
        "name": "has_complaint",
        "type": "boolean",
        "required": True,
        "description": (
            "是否含投诉。用户明确表达'我要投诉'或强烈不满为 true。"
            "仅情绪不佳但未表达投诉意愿则为 false。"
            "注意：has_complaint=true 时 sentiment 须为 angry 或 negative"
        ),
    },
    {
        "name": "was_escalated",
        "type": "boolean",
        "required": True,
        "description": "是否出现转人工/转接行为。对话中明确有'转人工''转接'即为 true",
    },
    # --- 标签与标记 ---
    {
        "name": "keywords",
        "type": "array",
        "items": {"type": "string"},
        "required": True,
        "description": (
            "3-5个关键词，提取对话中的实体词（商品名、动作、问题点），不要用元描述。"
            "正确示例：['蓝牙耳机', '左耳无声', '退款']。"
            "错误示例：['无实质内容', '咨询未展开']"
        ),
    },
    {
        "name": "attention_flags",
        "type": "array",
        "items": {"type": "string", "enum": list(VALID_ATTENTION_FLAGS)},
        "required": True,
        "description": (
            "需主管关注的标记，无特殊情况为空数组。"
            "舆情风险：angry + 投诉/曝光威胁同时满足。"
            "重复投诉：用户提及复发性问题。"
            "长时间未解决：等待超正常时效。"
            "用户流失：明确表示去别处。"
            "服务事故：客服明显失误"
        ),
    },
]

# ============================================================
# Function Calling 工具定义
# ============================================================

FUNCTION_NAME = "extract_conversation_info"


def build_function_definition() -> dict[str, Any]:
    """基于 FIELD_DEFINITIONS 生成 Function Calling 的 tool 定义。

    Returns:
        可直接传给 openai.chat.completions.create(tools=[...]) 的 dict。
    """
    properties: dict[str, Any] = {}
    required_fields: list[str] = []

    for field in FIELD_DEFINITIONS:
        prop: dict[str, Any] = {
            "type": field["type"],
            "description": field["description"],
        }
        if "enum" in field:
            prop["enum"] = field["enum"]
        if "items" in field:
            prop["items"] = field["items"]

        properties[field["name"]] = prop
        if field.get("required", False):
            required_fields.append(field["name"])

    return {
        "type": "function",
        "function": {
            "name": FUNCTION_NAME,
            "description": "从客服对话中提取结构化信息，用于客服主管周报统计",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_fields,
                "additionalProperties": False,
            },
        },
    }


def get_tool_choice() -> str:
    """生成 tool_choice 参数。

    DeepSeek 支持 "required" 强制调用函数，但不支持指定具体函数名。
    返回 "required"：模型必须调用 tools 中至少一个函数。
    """
    return "required"


# ============================================================
# 校验辅助
# ============================================================

def get_required_fields() -> list[str]:
    """返回所有 required 字段的名称列表。"""
    return [f["name"] for f in FIELD_DEFINITIONS if f.get("required", False)]


def get_field_enums() -> dict[str, set[str]]:
    """返回所有有枚举值的字段及其合法值集合。"""
    enums: dict[str, set[str]] = {}
    for f in FIELD_DEFINITIONS:
        if "enum" in f:
            enums[f["name"]] = set(f["enum"])
    return enums
