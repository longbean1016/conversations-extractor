# 客服对话信息提取工具

基于 LLM 的自动化工具，从客服对话中提取结构化信息，生成周报数据。

## 快速开始

```bash
pip install -r requirements.txt              # 安装依赖
cp .env.example .env                         # 编辑 .env 填入 API Key
cd solution && python main.py -v             # LLM 模式运行
cd solution && python main.py --mock -v      # Mock 模式运行（无需 API）
```

输出文件：`solution/extracted_results.json`，包含 25 条对话的结构化提取结果和汇总统计。

---

## 1. Schema 设计

面向"客服主管周报"场景，14 个字段分为 5 组：

| 分组 | 字段 | 设计理由 |
|------|------|----------|
| 基础信息 | `conversation_id` `channel` `agent` | 按渠道/客服分组统计 |
| 问题描述 | `summary` `primary_category` `secondary_categories` | 快速浏览摘要 + 问题分类饼图 |
| 解决状态 | `is_resolved` `resolution` `is_inquiry_only` | 核心 KPI 周解决率，is_inquiry_only 排除纯咨询类避免拉低指标 |
| 情绪风险 | `user_sentiment` `has_complaint` `was_escalated` | 情绪分布（angry/negative/neutral/positive）、投诉率、转人工率 |
| 标签标记 | `keywords` `attention_flags` | 词云检索 + 异常预警（舆情风险/重复投诉/用户流失/服务事故等） |

### 问题分类（8 类）

`商品质量` | `退款退货` | `物流配送` | `优惠促销` | `账号安全` | `商品咨询` | `功能建议` | `其他`

- 按问题根因分类。投诉情绪不单设类别，通过 `has_complaint` + `user_sentiment` 表达
- 退款/退货/换货/取消订单合并为 `退款退货`（本质都是订单变更）

### 情绪判断

| 值 | 触发特征 |
|----|----------|
| `angry` | 辱骂词汇、大量感叹号、明确投诉意愿 |
| `negative` | 不满但克制（"算了""行吧""好吧"） |
| `neutral` | 普通陈述（默认） |
| `positive` | 主动感谢或称赞 |

---

## 2. 实现方案

### 技术栈

Python + OpenAI SDK + DeepSeek 模型（`deepseek-v4-flash`）。

### 两种提取模式

| 模式 | 原理 | 适用场景 |
|------|------|----------|
| LLM 模式 | Function Calling，通过 `tools` 参数传入 JSON Schema，模型在 token 级受 Schema 约束 | 生产环境 |
| Mock 模式 | 关键词 + 规则匹配 | 快速验证、无网络环境 |

### 分层架构

```
0108-conversation/
├── 附件文件/                  ← 原始对话数据（不动）
│   ├── task2_conversations.json   # 25 条客服对话
│   └── task2_extract_example.md   # 提取示例参考
├── 开发与结果截图/            ← 运行结果 + 开发过程截图
│   ├── 提取完分布总结.png         # LLM 提取完成后的统计输出
│   ├── 终端使用.png               # python main.py -v 实时运行效果
│   ├── IDEA开发工具使用.png       # VS Code 开发环境
│   └── Agent工具使用.png          # Claude Code 辅助开发
├── 开发与结果截图说明/        ← 截图说明文档
│   └── 说明文档.md
├── planning/                  ← 设计文档
│   ├── DESIGN.md                  # 方案设计（Schema / 边界 / 架构）
│   ├── findings.md                # 数据分析记录
│   ├── task_plan.md               # 任务计划
│   └── progress.md                # 开发进度
├── solution/                  ← 核心代码
│   ├── main.py                    # CLI 入口（加载→提取→增量写入）
│   ├── config/
│   │   └── schema.py              # Schema 唯一定义（14字段/8分类/所有枚举）
│   ├── prompts/
│   │   └── system_prompt.py       # System Prompt（角色/规则/Few-shot示例）
│   ├── core/
│   │   ├── base.py                # Extractor 抽象接口 + 降级兜底
│   │   ├── llm_extractor.py       # LLM Function Calling 提取器
│   │   └── mock_extractor.py      # Mock 关键词规则提取器
│   └── utils/
│       ├── validation.py          # 后置校验（枚举/字段完整性）
│       ├── statistics.py          # 汇总统计（解决率/分类/情绪）
│       └── json_cleaner.py        # JSON 清洗（去 markdown 包裹）
├── .env.example                # API Key 配置模板
├── .gitignore                  # 排除 .env / __pycache__ / 生成结果
├── requirements.txt            # Python 依赖（openai, python-dotenv）
└── README.md                   # 本文档
```

---

## 3. 边界情况处理

| 边界类型 | 示例对话 | 处理策略 |
|----------|----------|----------|
| 多诉求并存 | conv_06（退货+快递） | primary 取首个/核心诉求，secondary 记录其余，summary 涵盖全部 |
| 转人工/升级 | conv_16 | was_escalated=true，转接后解决也保留标记 |
| 话题切换 | conv_09（骂机器人→退运费） | 以最终落地问题为主分类，keywords 保留切换痕迹 |
| 空对话 | conv_10 | is_inquiry_only=true，is_resolved=true，category=其他 |
| 信息缺失 | conv_12（不说型号→放弃） | is_resolved=false，resolution 说明原因，不标服务事故 |
| 情绪强烈/投诉 | conv_05 conv_09 | sentiment=angry，has_complaint=true，attention_flags 加舆情风险 |
| 重复问题用户 | conv_20（两次破损） | attention_flags 加重复投诉 |
| 用户流失 | conv_25（去别处买了） | is_resolved=false，attention_flags 加用户流失 |
| 对话中断恢复 | conv_24（问题被忽略） | attention_flags 加服务事故，summary 追溯原始问题 |

以上策略通过 System Prompt 中的 4 个 Few-shot 示例 + 6 条判断规则传递给 LLM。

---

## 4. 准确率验证

人工对照原始对话 JSON 和 `extracted_results.json`，抽取 5 条覆盖不同边界情况：

| 对话 | 覆盖要点 | 结果 |
|------|----------|:--:|
| conv_05 | angry + 投诉 + 商品质量 | ✓ 全对 |
| conv_06 | 多诉求（退货+快递） | ✓ 全对 |
| conv_09 | 话题切换 + 投诉情绪 | ✓ 全对 |
| conv_10 | 空对话/无实质内容 | ✓ 全对 |
| conv_16 | 转人工 + 长时间未解决 | ✓ 全对 |

**条级准确率**：5/5 = **100%**

---

## 5. AI 工具使用

本项目开发用 Claude Code 辅助完成：头脑风暴分析需求如果去做，写文档沉淀做法、数据分析和 Schema 设计、代码生成（分层架构）、Prompt 优化等操作，并且在本人测试之后，发现问题使用Claude Code进行Review的操作。
