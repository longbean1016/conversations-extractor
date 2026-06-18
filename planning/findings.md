# Findings & Decisions

## Requirements
<!-- Captured from user request -->
- 从每条客服对话中提取结构化信息，用于客服主管周报
- 自行设计完整 Schema（非简单套用示例），说明每个字段的设计理由
- 对 25 条对话自动提取，输出结构化 JSON
- 使用真实 LLM API（DeepSeek 模型，OpenAI 兼容接口，.env 配置）
- 处理边界情况：多诉求、转人工、话题切换、信息缺失等
- 人工抽检至少 5 条，报告准确率
- README：说明 schema 设计思路、任务拆解方式、AI 工具使用情况

## Research Findings
<!-- Key discoveries during exploration -->

### 数据特征分析（来自 task2_conversations.json）
- **总量**：25 条对话，在线 19 条 + 电话 6 条
- **客服**：小王 9 条 / 小李 8 条 / 小张 8 条
- **平均轮次**：约 4.6 轮（最短 3 轮，最长 6 轮）
- **问题类型分布**：
  - 退款相关：conv_01, conv_11, conv_16
  - 物流配送：conv_02, conv_14, conv_22
  - 商品质量：conv_05, conv_13, conv_20
  - 优惠券：conv_03
  - 账号安全：conv_04
  - 多诉求：conv_06
  - 退货：conv_07
  - 商品咨询：conv_08, conv_12, conv_17, conv_21
  - 投诉不满：conv_09, conv_25
  - 空对话：conv_10
  - 换货尺码：conv_18
  - 取消订单：conv_19
  - 功能建议：conv_23
  - 会话中断：conv_24

### 边界情况清单
| 类型 | 对话 | 特征 |
|------|------|------|
| 多诉求并存 | conv_06 | 同时问退货+快递 |
| 转人工/升级 | conv_16 | 要求转人工客服 |
| 话题切换 | conv_09 | 从骂机器人到问退货运费 |
| 空/无实质对话 | conv_10 | 用户说"我想想"后无下文 |
| 信息缺失/中途放弃 | conv_12 | 不说型号，最后算了 |
| 情绪强烈 | conv_05 | 骂人+感叹号+投诉 |
| 用户流失 | conv_25 | 等不及去别处买了 |
| 重复问题用户 | conv_20 | 两次收到问题商品 |
| 对话中断后恢复 | conv_24 | 上一轮问题被忽略 |

## Technical Decisions
<!-- Decisions made with rationale -->
| Decision | Rationale |
|----------|-----------|
| Python + openai 库 | DeepSeek 支持 OpenAI 兼容协议，openai 库最成熟 |
| 单轮提取策略 | 对话短（avg 4.6轮），单轮即可，延迟和成本更低 |
| 14 字段 Schema | 覆盖"聚合统计"和"下钻查看"两层需求 |
| 英文 field name | 便于程序处理，中文语义在 Prompt 中约束 |
| .env 配置 | API Key 等敏感信息不入代码库 |
| system prompt + user prompt 分离 | system 定义 schema，user 传入对话内容 |
| JSON mode / strict format | 要求 LLM 严格输出 JSON，便于程序解析 |
| 重试 1 次机制 | 应对偶发 API 超时/格式异常 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
|       |            |

## Resources
<!-- URLs, file paths, API references -->
- 项目目录：`D:\xiaoduo-interview\0108-conversation\`
- 数据文件：`task2_conversations.json`
- 示例文件：`task2_extract_example.md`
- OpenAI Python SDK：https://github.com/openai/openai-python

## Visual/Browser Findings
<!-- Multimodal content must be captured as text immediately -->
- 无需浏览器操作

---
*Update this file after every 2 view/browser/search operations*
