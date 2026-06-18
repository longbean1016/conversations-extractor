"""汇总统计：对提取结果生成聚合统计数据。"""


def generate_stats(results: list[dict]) -> dict:
    """生成汇总统计，供周报使用。

    Args:
        results: 提取结果列表

    Returns:
        统计 dict
    """
    total = len(results)
    if total == 0:
        return {"total_conversations": 0}

    resolved = sum(1 for r in results if r.get("is_resolved"))
    inquiry_only = sum(1 for r in results if r.get("is_inquiry_only"))
    complaint = sum(1 for r in results if r.get("has_complaint"))
    escalated = sum(1 for r in results if r.get("was_escalated"))
    errors = sum(1 for r in results if r.get("_extraction_error"))

    # 按分类统计
    category_count: dict[str, int] = {}
    for r in results:
        cat = r.get("primary_category", "未知")
        category_count[cat] = category_count.get(cat, 0) + 1

    # 按情绪统计
    sentiment_count: dict[str, int] = {}
    for r in results:
        sent = r.get("user_sentiment", "unknown")
        sentiment_count[sent] = sentiment_count.get(sent, 0) + 1

    # 按渠道统计
    channel_count: dict[str, int] = {}
    for r in results:
        ch = r.get("channel", "未知")
        channel_count[ch] = channel_count.get(ch, 0) + 1

    # 按客服统计
    agent_count: dict[str, int] = {}
    for r in results:
        ag = r.get("agent", "未知")
        agent_count[ag] = agent_count.get(ag, 0) + 1

    # 需关注标记
    flagged = [
        r
        for r in results
        if r.get("attention_flags") and len(r["attention_flags"]) > 0
    ]

    return {
        "total_conversations": total,
        "resolved_count": resolved,
        "resolution_rate": f"{resolved / max(total, 1) * 100:.1f}%",
        "inquiry_only_count": inquiry_only,
        "complaint_count": complaint,
        "escalated_count": escalated,
        "extraction_errors": errors,
        "by_category": category_count,
        "by_sentiment": sentiment_count,
        "by_channel": channel_count,
        "by_agent": agent_count,
        "flagged_for_attention": len(flagged),
    }
