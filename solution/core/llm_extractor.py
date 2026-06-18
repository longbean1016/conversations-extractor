"""
LLM 提取器：使用 Function Calling 技术进行结构化信息提取。

Schema 定义来自 config.schema，通过 tool definition 传递给模型。
模型必须在函数的 parameters 约束下输出，保证字段类型和枚举值正确。
"""

import json
import os
import time

import openai
from dotenv import load_dotenv

from config.schema import FUNCTION_NAME, build_function_definition
from core.base import Extractor, make_fallback_result
from prompts.system_prompt import SYSTEM_PROMPT, build_user_prompt
from utils.json_cleaner import clean_json_response

# .env 在项目根目录（solution/core/ → ../../）
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# --- LLM 客户端单例 ---

_client = None


def _get_client():
    """获取 OpenAI 兼容客户端（单例，延迟初始化）。"""
    global _client
    if _client is None:
        _client = openai.OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            timeout=float(os.getenv("REQUEST_TIMEOUT", "60")),
        )
    return _client


def _get_model() -> str:
    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


class LLMExtractor(Extractor):
    """基于 LLM Function Calling 的提取器。

    使用 OpenAI 兼容的 tools + tool_choice 参数，
    Schema 约束由 API 层面保障，而非依赖 Prompt 自然语言。
    """

    def __init__(self):
        self._client = _get_client()
        self._model = _get_model()
        self._max_retries = int(os.getenv("MAX_RETRIES", "1"))
        self._tool_definition = build_function_definition()

    def get_mode_name(self) -> str:
        return "llm"

    def extract(self, conversation: dict) -> dict:
        """提取单条对话的结构化信息。"""
        user_prompt = build_user_prompt(conversation)

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                if attempt > 0:
                    time.sleep(2)

                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    tools=[self._tool_definition],
                )

                result = self._parse_response(response)
                if result is not None:
                    result["conversation_id"] = conversation.get(
                        "id", result.get("conversation_id", "")
                    )
                    return result

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    continue

        return make_fallback_result(conversation, str(last_error) if last_error else "")

    def _parse_response(self, response) -> dict | None:
        """解析 Function Calling 响应。

        优先从 tool_calls 提取，兼容降级到 message.content。
        """
        message = response.choices[0].message

        # Function Calling 标准路径
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            if tool_call.function.name == FUNCTION_NAME:
                args = tool_call.function.arguments
                if args:
                    return json.loads(args)

        # 降级：部分模型可能将结果放在 content 中
        if message.content:
            cleaned = clean_json_response(message.content)
            if cleaned:
                return json.loads(cleaned)

        return None
