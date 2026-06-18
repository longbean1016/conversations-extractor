"""提取器抽象基类。"""

from abc import ABC, abstractmethod


class Extractor(ABC):
    """提取器接口。所有提取模式必须实现此接口。"""

    @abstractmethod
    def extract(self, conversation: dict) -> dict:
        """从单条对话中提取结构化信息。

        Args:
            conversation: 原始对话 dict（id, channel, agent, turns）

        Returns:
            提取结果 dict（14 字段 + 可能的 _extraction_error）
        """
        ...

    @abstractmethod
    def get_mode_name(self) -> str:
        """返回当前模式的名称（用于日志和输出）。"""
        ...


def make_fallback_result(conversation: dict, error: str = "") -> dict:
    """生成提取失败的默认结果。

    Args:
        conversation: 原始对话 dict
        error: 错误描述

    Returns:
        填充了默认值的 14 字段结果 dict
    """
    return {
        "conversation_id": conversation.get("id", "unknown"),
        "channel": conversation.get("channel", ""),
        "agent": conversation.get("agent", ""),
        "summary": f"提取失败: {error}" if error else "提取失败",
        "primary_category": "其他",
        "secondary_categories": [],
        "is_resolved": False,
        "resolution": "LLM 提取失败" if error else "处理异常",
        "is_inquiry_only": False,
        "user_sentiment": "neutral",
        "has_complaint": False,
        "was_escalated": False,
        "keywords": [],
        "attention_flags": [],
        "_extraction_error": True,
        "_error_detail": error,
    }
