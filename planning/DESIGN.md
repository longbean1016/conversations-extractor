# 客服对话信息提取工具 — 方案设计文档

## 一、背景与目标

客服主管每周需要了解所有客服对话的整体情况：用户问了什么、有没有解决、用户情绪怎么样。目前全靠逐条阅读对话，效率低下。本工具通过 LLM 自动从对话中提取结构化信息，支持主管快速浏览摘要和进行统计分析。

**输入**：25 条客服对话 JSON（`task2_conversations.json`）  
**输出**：结构化提取结果 JSON（`extracted_results.json`）  
**核心能力**：LLM 语义理解 → 结构化字段提取

---

## 二、Schema 设计

### 2.1 设计原则

面向"客服主管周报"场景，Schema 需要同时满足两个层次的需求：

| 层次 | 需求 | 对应字段 |
|------|------|----------|
| **聚合统计层** | 各类问题占比、解决率、情绪分布、投诉率 | category、is_resolved、sentiment、channel、agent |
| **下钻查看层** | 快速了解某条对话的完整情况 | summary、resolution、keywords、attention_flags |

### 2.2 完整字段定义

#### 基础信息（3 字段）

| # | 字段 | 类型 | 说明 | 设计理由 |
|---|------|------|------|----------|
| 1 | `conversation_id` | string | 对话唯一标识 | 与原始数据对应，便于溯源 |
| 2 | `channel` | string | `在线` / `电话` | 按渠道统计工作量、对比不同渠道的满意度和解决率 |
| 3 | `agent` | string | 客服姓名 | 按人统计处理量和解决率，用于绩效评估 |

#### 问题描述（3 字段）

| # | 字段 | 类型 | 说明 | 设计理由 |
|---|------|------|------|----------|
| 4 | `summary` | string | 一句话摘要（≤50字） | 主管快速浏览，替代逐条阅读原文。包含：用户诉求 + 处理结果 |
| 5 | `primary_category` | enum | 主要问题分类（见2.3） | 用于饼图统计，发现热点问题类型 |
| 6 | `secondary_categories` | array | 次要问题分类 | 多诉求场景下不丢失信息（如 conv_06 同时问退货和快递） |

#### 解决状态（3 字段）

| # | 字段 | 类型 | 说明 | 设计理由 |
|---|------|------|------|----------|
| 7 | `is_resolved` | bool | 问题是否解决 | 核心 KPI——周解决率。统计时排除纯咨询类对话 |
| 8 | `resolution` | string | 解决方案简述（≤30字） | 了解客服的常见处理方式，未解决时说明原因 |
| 9 | `is_inquiry_only` | bool | 是否为纯咨询（无售后问题） | 区分"咨询类"对话（如问成分、问能否上飞机），避免拉低解决率 |

> **`is_resolved` 判断标准**：  
> - `true`：问题得到明确答复或处理方案，用户接受（即使未最终完成，如"退款1-3天到账"）  
> - `false`：用户放弃、转出、信息不足无法处理、明确表示不满意  
> - 纯咨询类：`is_inquiry_only=true` 时 `is_resolved` 固定为 `true`

#### 情绪与风险（3 字段）

| # | 字段 | 类型 | 说明 | 设计理由 |
|---|------|------|------|----------|
| 10 | `user_sentiment` | enum | `positive` / `neutral` / `negative` / `angry` | 情绪分布统计，发现服务短板。angry 占比过高需重点关注 |
| 11 | `has_complaint` | bool | 是否包含投诉内容 | 计算投诉率（客服主动提"我要投诉"或明显不满表达） |
| 12 | `was_escalated` | bool | 是否转人工/升级处理 | 评估前置渠道（机器人等）的拦截效果。仅当对话中明确出现"转人工"等行为时为 true |

#### 标签与标记（2 字段）

| # | 字段 | 类型 | 说明 | 设计理由 |
|---|------|------|------|----------|
| 13 | `keywords` | array(string) | 关键词标签（3-5 个） | 用于词云、趋势分析、快速检索 |
| 14 | `attention_flags` | array(string) | 需主管关注的标记 | 标记异常对话，主管可优先查看。取值：`舆情风险` / `重复投诉` / `长时间未解决` / `用户流失` / `服务事故` |

### 2.3 `primary_category` 枚举值（8 类）

基于 25 条对话数据归纳，精简为 8 类，按问题本质而非情绪分类：

| 值 | 说明 | 示例对话 |
|----|------|----------|
| `商品质量` | 商品破损、故障、品控问题 | conv_05, conv_13, conv_20 |
| `退款退货` | 退款/退货/换货/取消/退运费等订单变更 | conv_01, conv_06, conv_07, conv_11, conv_15, conv_16, conv_18, conv_19 |
| `物流配送` | 快递未收到、改地址、放错快递柜 | conv_02, conv_14, conv_22 |
| `优惠促销` | 优惠券使用条件、促销活动 | conv_03 |
| `账号安全` | 异地登录、密码修改、二次验证 | conv_04 |
| `商品咨询` | 产品参数、库存、成分、对比 | conv_08, conv_12, conv_17, conv_21 |
| `功能建议` | 用户建议新功能 | conv_23 |
| `其他` | 无法归类的情况 | conv_10（无实质内容）, conv_24, conv_25 |

> **设计原则**：删除了 `投诉不满` 分类（投诉是情绪维度，已通过 `has_complaint` + `user_sentiment` 覆盖）。合并 `退款相关` + `换货尺码` + `取消订单` → `退款退货`（本质都是订单变更操作）。从 11 类精简为 8 类，边界更清晰。

### 2.4 情绪判断标准

| 值 | 触发特征 | 对话示例 |
|----|----------|----------|
| `angry` | 骂人、人身攻击、大量感叹号（3+）、明确"我要投诉" | conv_05："你们什么破服务！！"；conv_09："智障！" |
| `negative` | 不满但克制，抱怨、"算了""行吧""再等等"等消极接受 | conv_11："行吧 再等等"；conv_18："好吧" |
| `neutral` | 普通陈述，无明显情绪波动 | conv_01：正常描述问题 |
| `positive` | 感谢、满意、称赞 | conv_08："好的谢谢" |

---

## 三、技术方案

### 3.1 架构概览

```
task2_conversations.json
        │
        ▼
┌──────────────────┐
│   主流程脚本      │
│   main.py        │
│                  │
│  1. 加载对话数据  │
│  2. 逐条调用 LLM  │
│  3. 解析 JSON     │
│  4. 汇总输出      │
└──────┬───────────┘
       │ 逐条调用
       ▼
┌──────────────────┐
│   LLM 客户端      │
│   llm_client.py  │
│                  │
│  - Prompt 模板   │
│  - API 调用      │
│  - 重试逻辑      │
│  - JSON 校验     │
└──────┬───────────┘
       │ OpenAI 兼容协议
       ▼
┌──────────────────┐
│   DeepSeek API   │
│   (deepseek-chat)│
└──────────────────┘
```

### 3.2 技术选型

| 选项 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3 | 生态成熟，openai 库支持完善 |
| LLM SDK | `openai` 官方库 | DeepSeek 完全兼容 OpenAI 协议 |
| 模型 | `deepseek-chat` | 性价比高，中文理解能力强 |
| 配置管理 | `python-dotenv` | API Key 通过 .env 隔离 |
| 提取策略 | 单轮提取 | 对话短（avg 4.6轮），单次 API 调用足够 |

### 3.3 Prompt 设计

采用 **system prompt + user prompt** 分离模式：

- **System Prompt**：定义角色（客服质检专家）、完整的 14 字段 Schema、每个字段的取值约束、边界情况处理规则
- **User Prompt**：传入单条对话的 JSON 文本，要求严格输出 JSON

关键约束：
- 要求输出纯 JSON（不含 markdown 代码块标记），便于 `json.loads()` 直接解析
- 使用 `response_format: { type: "json_object" }` 参数（DeepSeek 支持）
- 在 Prompt 中明确所有枚举值的完整列表

### 3.4 错误处理

| 场景 | 策略 |
|------|------|
| API 超时/网络错误 | 重试 1 次，间隔 2 秒 |
| 返回非 JSON | 尝试提取 JSON 子串；失败则标记 `extraction_error` |
| 字段缺失 | 用 null/默认值填充，不阻塞流程 |
| 枚举值越界 | 记录警告，保留原值（便于后续分析 Prompt 不足） |

### 3.5 输出格式

```json
{
  "extracted_at": "2026-06-17T10:00:00",
  "model": "deepseek-chat",
  "total_conversations": 25,
  "success_count": 25,
  "error_count": 0,
  "results": [
    {
      "conversation_id": "conv_01",
      "channel": "在线",
      "agent": "小王",
      "summary": "...",
      "primary_category": "退款相关",
      "secondary_categories": [],
      "is_resolved": true,
      "resolution": "...",
      "is_inquiry_only": false,
      "user_sentiment": "neutral",
      "has_complaint": false,
      "was_escalated": false,
      "keywords": ["蓝牙耳机", "左耳无声", "退款"],
      "attention_flags": []
    }
  ]
}
```

---

## 四、边界情况处理策略

基于对 25 条对话数据的分析，识别出以下 9 类边界情况：

### 4.1 多诉求并存

| 对话 | 特征 | 处理策略 |
|------|------|----------|
| conv_06 | 同时问退货进度 + 快递状态 | `primary_category` 取首个/核心诉求（退款相关），`secondary_categories` 记录第二个（物流配送）。`summary` 涵盖全部诉求 |

**Prompt 约束**：如对话涉及多个不同类别的问题，primary 取用户最关心的一个（通常最先提出或情绪投入最多的），其余放入 secondary。

### 4.2 转人工/升级处理

| 对话 | 特征 | 处理策略 |
|------|------|----------|
| conv_16 | 用户要求转人工，角色切换前后 | `was_escalated: true`。即使后续问题被解决，也标记为已升级。`summary` 注明升级原因 |

### 4.3 话题切换

| 对话 | 特征 | 处理策略 |
|------|------|----------|
| conv_09 | 骂机器人 → 问退货运费 | `summary` 涵盖最终落地话题（退货运费），`keywords` 包含切换前后关键词。`primary_category` 以最终问题为准 |

**原则**：以对话最终落地的问题为主分类，但摘要和关键词保留话题切换的痕迹。

### 4.4 空对话/无实质内容

| 对话 | 特征 | 处理策略 |
|------|------|----------|
| conv_10 | 用户说"嗯嗯我想想"后无下文 | `is_inquiry_only: true`，`is_resolved: true`（无待解决问题），`primary_category: 其他`，`summary` 诚实描述"用户未提出具体问题" |

### 4.5 信息缺失/用户放弃提供

| 对话 | 特征 | 处理策略 |
|------|------|----------|
| conv_12 | 用户不说型号，最后"算了不看了" | `is_resolved: false`，`resolution` 注明"用户未提供足够信息，自行放弃" |

### 4.6 情绪强烈/含投诉

| 对话 | 特征 | 处理策略 |
|------|------|----------|
| conv_05 | 骂人、大量感叹号 | `user_sentiment: angry`，`has_complaint: true`，`attention_flags` 加入 `服务事故` |
| conv_09 | "智障"等辱骂词汇 | `user_sentiment: angry`，`has_complaint: true` |

### 4.7 重复问题用户

| 对话 | 特征 | 处理策略 |
|------|------|----------|
| conv_20 | 两次收到问题商品 | `attention_flags` 加入 `重复投诉`，提醒主管这是复发性问题，需品控跟进 |

### 4.8 用户流失/对话中断

| 对话 | 特征 | 处理策略 |
|------|------|----------|
| conv_25 | 等不及，去别处买了 | `is_resolved: false`，`attention_flags` 加入 `用户流失`，`resolution` 注明"用户因等待时间过长放弃" |
| conv_24 | 上一轮问题被忽略 | `summary` 追溯原始问题（蓝牙耳机颜色），`attention_flags` 加入 `服务事故` |

### 4.9 纯建议/非问题类

| 对话 | 特征 | 处理策略 |
|------|------|----------|
| conv_23 | 用户提建议（实物视频功能） | `is_inquiry_only: true`，`primary_category: 功能建议`，`summary` 概括建议内容 |

---

## 五、准确率验证方案

### 5.1 抽样策略

从 25 条中随机抽取 5 条，需覆盖不同类别和边界情况：

| 要求 | 覆盖 |
|------|------|
| 不同问题类型 | 至少 4 种 primary_category |
| 不同情绪 | 至少包含 neutral / negative / angry |
| 边界情况 | 至少 2 种边界类型 |
| 不同渠道 | 在线 + 电话 |
| 不同客服 | 至少 3 位客服 |

### 5.2 评分标准

逐字段对比人工判断与 LLM 输出：

| 等级 | 标准 | 示例 |
|------|------|------|
| ✓ 正确 | 与人工判断完全一致 | LLM 输出 `angry`，人工也判为 `angry` |
| △ 部分正确 | 方向对但不够精确 | LLM 输出 `退款相关`，人工判为 `商品质量`（其实是质量→退款） |
| ✗ 错误 | 明显错误 | LLM 输出 `positive`，实际用户非常不满 |

### 5.3 报告指标

- **字段级准确率**：每个字段的正确数 / 抽样总数（5条）
- **条级准确率**：整条"所有字段正确"的条数 / 5
- **关键字段准确率**：summary / primary_category / is_resolved / user_sentiment 四个核心字段的正确率

---

## 六、项目文件结构

```
0108-conversation/
├── .env                    # API Key 配置（不入版本控制）
├── .env.example            # 配置模板
├── task2_conversations.json  # 原始数据
├── task2_extract_example.md  # 示例参考
├── main.py                 # 主流程
├── llm_client.py           # LLM 调用模块
├── prompt.py               # Prompt 模板
├── validate.py             # 准确率验证脚本
├── extracted_results.json  # 输出结果
├── DESIGN.md               # 本设计文档
├── README.md               # 项目说明
├── task_plan.md            # 任务计划
├── findings.md             # 研究发现
└── progress.md             # 进度日志
```

---

## 七、依赖

```
openai>=1.0.0
python-dotenv>=1.0.0
```

---

*文档版本：v1.0 | 日期：2026-06-17*
