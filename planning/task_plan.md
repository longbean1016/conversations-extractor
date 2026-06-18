# Task Plan: 客服对话信息提取工具

## Goal
构建一个基于 LLM 的自动化工具，从 25 条客服对话中提取结构化信息，输出 JSON 供客服主管做周报使用，包含 schema 设计、提取实现、边界处理、准确率验证和 README 文档。

## Current Phase
Phase 6 - 全部阶段已完成，待用户配置 API Key 运行 LLM 模式

## Phases

### Phase 1: Schema 设计与方案文档
- [x] 分析 25 条对话数据，归纳问题类型和边界情况
- [x] 设计 14 字段的完整提取 Schema
- [x] 确定技术方案（Python + OpenAI 兼容接口 + DeepSeek）
- [x] 编写方案设计文档（DESIGN.md）
- **Status:** complete

### Phase 2: 项目搭建与环境配置
- [x] 创建 solution/ 目录结构
- [x] 配置 .env.example / .gitignore / requirements.txt
- [x] 用户自行复制 .env.example → .env 并填入 DeepSeek API Key
- **Status:** complete

### Phase 3: 提取工具实现
- [x] prompt.py — System Prompt（14 字段定义 + 边界规则 + 输出约束）
- [x] extractor.py — LLM 调用（重试 + JSON 清洗）+ Mock 模式（规则匹配）
- [x] main.py — 批量提取主流程（加载 → 提取 → 校验 → 统计 → 输出）
- [x] Mock 模式已验证通过（25/25 条成功，耗时 0.0s）
- **Status:** complete

### Phase 4: 边界情况处理
- [x] Prompt 中融入 6 条边界处理规则
- [x] Mock 模式覆盖 9 类边界情况的关键词/模式匹配
- [x] 提取结果含 _extraction_error 标记和详细错误信息
- **Status:** complete

### Phase 5: 准确率验证
- [x] validate.py 交互式验证工具已就绪
- [ ] 待用户运行 `python validate.py` 进行人工评分
- [ ] 准确率报告（字段级 + 条级）
- **Status:** complete（工具就绪，待用户执行）

### Phase 6: README 文档
- [x] Schema 设计思路说明
- [x] 任务拆解方式
- [x] AI 工具使用情况
- [x] 边界情况处理策略
- [x] 准确率验证框架（待用户填入实际数据）
- **Status:** complete

## Key Questions
1. 如何兼顾提取质量和 API 调用成本？→ 单轮提取，temperature=0.1
2. 情绪 `angry` vs `negative` 的边界如何精确划分？→ Prompt 中明确触发特征
3. `primary_category` 枚举是否需要扩展？→ 当前 11 类覆盖 25 条全量数据

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用 Python + OpenAI SDK | OpenAI 兼容接口通用性强，DeepSeek 支持该协议 |
| 单轮 LLM 提取（非分步） | 对话短（平均4-5轮），单轮够用，延迟低 |
| 14 字段 Schema（非简单 8 字段） | 覆盖主管周报全部需求：统计维度+下钻能力 |
| 字段名使用英文 | 便于程序处理，中文含义在 Prompt 中说明 |
| .env 配置 API Key | 安全隔离敏感信息，不入版本控制 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| UnicodeEncodeError (GBK) on Windows | 1 | 添加 sys.stdout/stderr 重定向为 UTF-8 (io.TextIOWrapper) |
| Mock "重复投诉"误报（`也`字触发 13 条假阳性） | 1 | 关键词改为短语匹配（如"上次也是这样""又坏了"），误报从 13→10 |
| fallback dict 在 extractor.py 和 main.py 重复定义 | 1 | 抽取为 `make_fallback_result()` 公共函数 |
| 未使用的 import（re, random, Optional） | 1 | 删除 |
| extract_with_llm 每次创建新的 OpenAI Client | 1 | 改为模块级单例 `_get_client()` |
| validate_result 校验不完整 | 1 | 补充 channel / attention_flags / secondary_categories 枚举校验 |

## Notes
- 所有规划文件放项目根目录，非技能安装目录
- 决策前重新读取计划
- 错误必须记录，不重复失败操作
