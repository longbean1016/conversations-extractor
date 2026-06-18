"""
Mock 提取器：基于规则匹配，无需 API Key。
用于快速测试和对比基线。
"""

from core.base import Extractor

# ============================================================
# 规则匹配表
# ============================================================

CATEGORY_KEYWORDS = {
    "商品质量": ["坏的", "碎了", "破损", "坏了", "不工作", "故障", "品控", "假货", "色差"],
    "退款退货": [
        "退款", "到账", "退钱", "款项", "退货", "换尺码", "换号",
        "尺码", "大小", "部分退货", "只想退其中一个", "换新", "取消",
        "还没发货", "退货运费",
    ],
    "物流配送": [
        "快递", "物流", "配送", "签收", "派送", "快递柜",
        "改地址", "改派送", "送货",
    ],
    "优惠促销": ["优惠券", "满", "折扣", "促销"],
    "账号安全": ["异地登录", "密码", "验证", "账号安全"],
    "商品咨询": ["成分", "能不能带上", "有货", "补货", "哪个好", "对比", "推荐", "颜色", "库存"],
    "功能建议": ["建议", "能不能加", "功能"],
}

SENTIMENT_PATTERNS = {
    "angry": ["什么破", "智障", "！！！", "！！", "投诉", "浪费我时间", "tmd", "TMD"],
    "negative": ["算了", "行吧", "好吧", "再等等", "有点", "失望", "没信心", "搞半天"],
    "positive": ["谢谢", "好的谢谢", "感谢", "不错", "很好"],
}

COMPLAINT_KEYWORDS = ["投诉", "什么破", "没人理", "智障", "我要投诉"]

ESCALATION_KEYWORDS = ["转接", "转人工"]

ATTENTION_DUPLICATE_KW = [
    "上次也是这样", "又坏了", "又出现问题", "之前也是",
    "两次", "连续两次", "又出现", "再次",
]

ATTENTION_LONG_WAIT_KW = [
    "五天", "一周", "三天", "好几天", "好久", "半天", "20分钟", "半天了",
]

ATTENTION_CHURN_KW = ["别的地方买", "别处买", "不在你们这买了", "不用了"]

ATTENTION_SERVICE_KW = ["怎么不回了", "没人理我", "半天没人回"]

PRODUCT_KEYWORDS = [
    "蓝牙耳机", "手机壳", "充电宝", "衣服", "面膜", "杯子", "碗",
    "双肩包", "扫地机器人", "手机", "T恤", "衬衫",
]


class MockExtractor(Extractor):
    """基于关键词和模式匹配的提取器。

    无需 API Key，结果可复现，用于：
    - 快速验证项目流程
    - 作为 LLM 提取的对比基线
    - 无网络环境下的降级方案
    """

    def get_mode_name(self) -> str:
        return "mock"

    def extract(self, conversation: dict) -> dict:
        conv_id = conversation.get("id", "unknown")
        channel = conversation.get("channel", "在线")
        agent = conversation.get("agent", "未知")
        turns = conversation.get("turns", [])

        user_text = " ".join(
            t.get("content", "") for t in turns if t.get("role") == "user"
        )
        agent_text = " ".join(
            t.get("content", "") for t in turns if t.get("role") == "agent"
        )

        primary, secondary = self._classify_category(user_text)
        sentiment = self._classify_sentiment(user_text)
        has_complaint = self._detect_complaint(user_text)
        was_escalated = self._detect_escalation(turns)
        is_inquiry = self._is_inquiry(primary)
        is_resolved = self._determine_resolved(is_inquiry, turns)
        summary = self._make_summary(is_resolved, user_text)
        resolution = self._make_resolution(is_resolved)
        keywords = self._extract_keywords(user_text, primary)
        attention_flags = self._get_attention_flags(
            user_text, sentiment, has_complaint
        )

        return {
            "conversation_id": conv_id,
            "channel": channel,
            "agent": agent,
            "summary": summary,
            "primary_category": primary,
            "secondary_categories": secondary,
            "is_resolved": is_resolved,
            "resolution": resolution,
            "is_inquiry_only": is_inquiry,
            "user_sentiment": sentiment,
            "has_complaint": has_complaint,
            "was_escalated": was_escalated,
            "keywords": keywords,
            "attention_flags": attention_flags,
        }

    # ---- 内部方法 ----

    def _classify_category(self, text: str) -> tuple[str, list[str]]:
        scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[category] = score
        if not scores:
            return "其他", []
        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_cats[0][0]
        secondary = (
            [cat for cat, _ in sorted_cats[1:]] if len(sorted_cats) > 1 else []
        )
        return primary, secondary

    def _classify_sentiment(self, text: str) -> str:
        for sentiment, patterns in SENTIMENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    return sentiment
        return "neutral"

    @staticmethod
    def _detect_complaint(text: str) -> bool:
        return any(kw in text for kw in COMPLAINT_KEYWORDS)

    @staticmethod
    def _detect_escalation(turns: list[dict]) -> bool:
        for turn in turns:
            content = turn.get("content", "")
            if any(kw in content for kw in ESCALATION_KEYWORDS):
                return True
        return False

    @staticmethod
    def _is_inquiry(primary: str) -> bool:
        return primary in ("商品咨询", "功能建议")

    def _determine_resolved(
        self, is_inquiry: bool, turns: list[dict]
    ) -> bool:
        if is_inquiry:
            return True
        last_turn = turns[-1] if turns else {}
        last_role = last_turn.get("role", "")
        return not (
            last_role == "user"
            and self._classify_sentiment(last_turn.get("content", ""))
            in ("negative", "angry")
        )

    @staticmethod
    def _make_summary(is_resolved: bool, user_text: str) -> str:
        sentences = user_text.replace("？", "。").split("。")
        first_sent = ""
        for s in sentences:
            s = s.strip()
            if len(s) >= 8:
                first_sent = s[:40]
                break
        if not first_sent:
            first_sent = sentences[0].strip()[:40] if sentences else user_text[:40]
        status = "已解决" if is_resolved else "未解决"
        return f"{first_sent}（{status}）"

    @staticmethod
    def _make_resolution(is_resolved: bool) -> str:
        return "客服已提供解决方案" if is_resolved else "问题未解决"

    @staticmethod
    def _extract_keywords(user_text: str, category: str) -> list[str]:
        keywords = []
        for kw in PRODUCT_KEYWORDS:
            if kw in user_text:
                keywords.append(kw)
        if category:
            keywords.insert(0, category)
        return keywords[:5]

    @staticmethod
    def _get_attention_flags(
        text: str, sentiment: str, has_complaint: bool
    ) -> list[str]:
        flags = []

        if sentiment == "angry" and has_complaint:
            flags.append("舆情风险")

        if any(kw in text for kw in ATTENTION_DUPLICATE_KW):
            flags.append("重复投诉")

        if any(kw in text for kw in ATTENTION_LONG_WAIT_KW):
            flags.append("长时间未解决")

        if any(kw in text for kw in ATTENTION_CHURN_KW):
            flags.append("用户流失")

        if any(kw in text for kw in ATTENTION_SERVICE_KW):
            flags.append("服务事故")

        return flags
