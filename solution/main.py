#!/usr/bin/env python3
"""
客服对话信息提取工具 — 主流程（薄编排层）。

职责：加载数据 → 选择提取器 → 批量提取 → 校验 → 统计 → 输出。
核心逻辑全部在 core/ 和 utils/ 中。
"""

import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

# 修复 Windows GBK 编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from core.base import make_fallback_result
from core.llm_extractor import LLMExtractor
from core.mock_extractor import MockExtractor
from utils.statistics import generate_stats
from utils.validation import validate_result

# 路径配置
DATA_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "附件文件", "task2_conversations.json"))
OUTPUT_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "extracted_results.json"))
CST = timezone(timedelta(hours=8))


def load_conversations(filepath: str) -> list[dict]:
    """加载对话数据。"""
    if not os.path.exists(filepath):
        print(f"错误: 找不到数据文件 {filepath}")
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"已加载 {len(data)} 条对话")
    return data


def select_extractor(use_mock: bool):
    """根据模式选择提取器。"""
    if use_mock:
        return MockExtractor()
    return LLMExtractor()


def print_result_verbose(result: dict):
    """实时打印单条提取结果的关键字段。"""
    cat_str = result.get('primary_category', '?')
    sec = result.get("secondary_categories", [])
    if sec:
        cat_str += f" + {sec}"
    print(f"  摘要: {result.get('summary', '?')}", flush=True)
    print(f"  分类: {cat_str}", flush=True)
    print(f"  情绪: {result.get('user_sentiment', '?')} | "
          f"解决: {'是' if result.get('is_resolved') else '否'} | "
          f"投诉: {'是' if result.get('has_complaint') else '否'} | "
          f"转人工: {'是' if result.get('was_escalated') else '否'}", flush=True)
    flags = result.get("attention_flags", [])
    if flags:
        print(f"  ⚡ 关注: {', '.join(flags)}", flush=True)


def save_snapshot(results: list[dict], validation_issues: dict, mode_name: str):
    """每提取一条就增量写入 JSON 文件，防止中途崩溃丢失结果。"""
    stats = generate_stats(results)
    output = {
        "extracted_at": datetime.now(CST).isoformat(),
        "mode": mode_name,
        "statistics": stats,
        "validation_issues": validation_issues,
        "results": results,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def run_extraction(
    extractor, conversations: list[dict], verbose: bool = False
) -> tuple[list[dict], dict]:
    """执行批量提取，返回 (结果列表, 校验问题 dict)。"""
    results = []
    validation_issues: dict[str, list[str]] = {}
    start_time = time.time()

    print(f"开始提取，共 {len(conversations)} 条...\n")

    for i, conv in enumerate(conversations):
        conv_id = conv.get("id", f"conv_{i}")
        print(f"[{i+1}/{len(conversations)}] 正在处理 {conv_id}...", end=" ", flush=True)

        try:
            result = extractor.extract(conv)
            issues = validate_result(result)
            if issues:
                validation_issues[conv_id] = issues
                print(f"⚠ {issues}", flush=True)
            else:
                print("✓", flush=True)
            results.append(result)

            # 增量写入：每完成一条立刻落盘
            save_snapshot(results, validation_issues, extractor.get_mode_name())

            if verbose and not result.get("_extraction_error"):
                print_result_verbose(result)

        except Exception as e:
            print(f"✗ {e}", flush=True)
            results.append(make_fallback_result(conv, str(e)))
            save_snapshot(results, validation_issues, extractor.get_mode_name())

        # LLM 模式加间隔防止限流
        if not isinstance(extractor, MockExtractor):
            time.sleep(0.5)

    elapsed = time.time() - start_time
    print(f"\n耗时 {elapsed:.1f}s")
    return results, validation_issues


def main():
    use_mock = "--mock" in sys.argv or "-m" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    mode_label = "Mock（规则匹配）" if use_mock else "LLM API + Function Calling"
    print(f"模式: {mode_label}{'（实时输出）' if verbose else ''}")

    conversations = load_conversations(DATA_FILE)
    extractor = select_extractor(use_mock)
    results, validation_issues = run_extraction(extractor, conversations, verbose=verbose)

    # 统计
    stats = generate_stats(results)

    # 输出
    output = {
        "extracted_at": datetime.now(CST).isoformat(),
        "mode": extractor.get_mode_name(),
        "statistics": stats,
        "validation_issues": validation_issues,
        "results": results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 摘要
    print(f"\n{'='*50}")
    print(f"总计: {stats['total_conversations']} 条")
    print(f"解决率: {stats['resolution_rate']}")
    print(f"投诉数: {stats['complaint_count']} | 转人工: {stats['escalated_count']}")
    print(f"提取错误: {stats['extraction_errors']} | 需关注: {stats['flagged_for_attention']}")

    if validation_issues:
        print(f"校验警告: {len(validation_issues)} 条")

    print(f"\n分类分布:")
    for cat, count in sorted(
        stats["by_category"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {cat}: {count}")

    print(f"\n情绪分布:")
    for sent, count in stats["by_sentiment"].items():
        print(f"  {sent}: {count}")

    print(f"\n结果: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
