# 断板反包专家 - 完整技能手册

## 一、数据查询类

### 1. 断板数据
```bash
# 断板排名（昨日收盘）
curl http://localhost:8000/api/duanban/ranking

# 断板扫描（实时）
curl -X POST http://localhost:8000/api/duanban/scan

# 断板历史
curl http://localhost:8000/api/duanban/history

# 个股断板研报
curl http://localhost:8000/api/duanban/report/{code}
```

### 2. 连板天梯
```bash
# 连板数据
curl http://localhost:8000/api/lianban/enhanced/$(date +%Y%m%d)

# 连板晋级率
curl http://localhost:8000/api/lianban/index-promotion/$(date +%Y%m%d)

# 连板趋势
curl http://localhost:8000/api/lianban/index-trend
```

### 3. 妖股数据（重要！）
```bash
# 妖股榜单
curl http://localhost:8000/api/yaogu/list

# 妖股详情
curl http://localhost:8000/api/yaogu/{code}

# 妖股买入区间
curl http://localhost:8000/api/yaogu/trade-zones/{code}

# 妖股历史表现
curl http://localhost:8000/api/yaogu/history/{code}

# 两只股票对比（Gemini分析）
curl -X POST http://localhost:8000/api/yaogu/ai/analyze \
  -H "Content-Type: application/json" \
  -d '{"codes": ["000001", "000002"], "question": "哪只更值得买入？"}'
```

### 4. 优选标的
```bash
# 优选标的列表
curl http://localhost:8000/api/selected-stocks

# 推荐标的
curl http://localhost:8000/api/selected-stocks/recommend

# 买入机会
curl http://localhost:8000/api/selected-stocks/buy-opportunity

# 高盈利标的
curl http://localhost:8000/api/selected-stocks/high-profit
```

---

## 二、研报类

### 1. 内部研报
```bash
# 研报列表
curl http://localhost:8000/api/reports

# 个股研报
curl http://localhost:8000/api/reports/by-stock/{code}

# 研报详情
curl http://localhost:8000/api/reports/{report_id}
```

### 2. Gemini DeepResearch（深度调研 - 重要！）

**核心能力**：板块调研 + 个股调研，从板块找机会

```bash
# 板块深度调研（盘前/盘后必做！）
curl -X POST http://localhost:8000/api/gemini/research/save \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-01-30",
    "prompt": "分析A股当前热门板块机会：\n1)哪些板块近期资金流入明显\n2)哪些板块有政策利好\n3)哪些板块龙头走势健康\n4)明日重点关注哪些板块\n5)风险提示",
    "task_type": "sector_analysis",
    "priority": 85,
    "auto_submit": true
  }'

# 个股深度研报
curl -X POST http://localhost:8000/api/gemini/research/save \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-01-30",
    "prompt": "分析天奇股份(002009)的投资价值：1)公司基本面 2)所属概念板块 3)近期资金流向 4)短线交易机会 5)风险提示",
    "task_type": "stock_analysis",
    "priority": 80,
    "auto_submit": true
  }'

# 查询研报任务
curl http://localhost:8000/api/gemini/research/tasks

# 获取研报结果
curl http://localhost:8000/api/gemini/research/report/{task_id}
```

**使用时机**：
- **盘前**：提交板块调研 → 确定今日重点板块 → 从板块找标的
- **盘后**：提交板块调研 → 分析明日板块机会 → 为明日做准备

**从板块找机会的流程**：
1. 提交板块调研任务
2. 确定重点板块方向
3. 在重点板块中找龙头/前排股
4. 为具体标的提交个股研报

### 3. 研报摘要（AnythingLLM）
```bash
# 研报摘要
curl http://localhost:8000/api/anythingllm/report-summary/{code}

# 是否可以买入分析
curl http://localhost:8000/api/anythingllm/can-buy/{code}

# 交易机会卡片
curl http://localhost:8000/api/anythingllm/deal-cards
```

---

## 三、市场数据类

### 1. 市场简报
```bash
# 早盘简报
curl http://localhost:8000/api/market/briefing/$(date +%Y%m%d)/pre

# 午盘简报
curl http://localhost:8000/api/market/briefing/$(date +%Y%m%d)/mid

# 收盘简报
curl http://localhost:8000/api/market/briefing/$(date +%Y%m%d)/post

# AI早盘简报
curl http://localhost:8000/api/anythingllm/morning-briefing
```

### 2. 板块/概念数据（重要！）

**核心方法论**：同板块前排龙头互相参照决策

```bash
# 获取个股所属概念板块
curl http://localhost:8000/api/yaogu/detail/{code}/concept-plates
# 返回: {"reasons": [{"name": "人形机器人", "count": 10}, {"name": "优必选", "count": 5}...]}

# 获取龙头标签概念列表（看哪些板块有龙头）
curl http://localhost:8000/api/yaogu/leader-tags/concepts
# 返回: [{"name": "机器人", "count": 219}, {"name": "半导体", "count": 170}...]

# 获取概念龙头
curl http://localhost:8000/api/yaogu/concepts/{concept}/leaders

# 市场情绪（多板指数、涨停家数等）
curl http://localhost:8000/api/market/index/summary
# 返回: 情绪分数、多板指数、涨停家数、跌停家数等
```

**参考对标股用法**：
1. 查询标的所属板块（concept-plates）
2. 找到同板块其他龙头（concepts/{板块}/leaders）
3. 将参考股加入观察列表
4. 盘中观察参考股作为买卖决策参考
   - 参考股走强 → 持仓可多拿
   - 参考股走弱 → 警惕风险
   - 参考股涨停 → 板块情绪可能升温

### 3. 新闻资讯
```bash
# 最新新闻
curl http://localhost:8000/api/news/list?limit=20

# 新闻摘要
curl http://localhost:8000/api/news/summary/$(date +%Y-%m-%d)

# 个股新闻
curl http://localhost:8000/api/yaogu/news/{code}

# 龙头热度检查
curl http://localhost:8000/api/yaogu/news/leader-hot-check/{code}
```

### 4. 指数数据
```bash
# 指数实时
curl http://localhost:8000/api/market/index/realtime

# 指数摘要
curl http://localhost:8000/api/market/index/summary

# 指数AI分析
curl http://localhost:8000/api/market/index/ai-analyze
```

### 5. 个股实时行情（新增）
```bash
# 单只股票
curl http://localhost:8000/api/market/realtime/003042

# 多只股票（逗号分隔）
curl http://localhost:8000/api/market/realtime/003042,002119,000001

# 返回: {"data": {"003042": {"name": "中农联合", "price": 20.58, "change_pct": -10.01, ...}}}
```

---

## 四、竞价数据类

```bash
# 竞价突破信号
curl http://localhost:8000/api/auction/breakout/signals

# 竞价候选
curl http://localhost:8000/api/auction/breakout/candidates

# 竞价简报
curl http://localhost:8000/api/auction/briefing/latest

# 竞价筛选
curl http://localhost:8000/api/screening/auction/screen
```

---

## 五、交易相关类

### 1. 虚拟账户
```bash
# 查看账户
curl http://localhost:9001/api/account/{agent_id}

# 查看持仓
curl http://localhost:9001/api/account/{agent_id}/positions

# 买入
curl -X POST http://localhost:9001/api/account/{agent_id}/buy \
  -H "Content-Type: application/json" \
  -d '{"code": "000001", "name": "平安银行", "price": 10.5, "quantity": 100, "reason": "买入理由"}'

# 卖出
curl -X POST http://localhost:9001/api/account/{agent_id}/sell \
  -H "Content-Type: application/json" \
  -d '{"code": "000001", "price": 11.0, "quantity": 100, "reason": "卖出理由"}'
```

### 2. 交易计划
```bash
# 获取交易计划
curl http://localhost:8000/api/plans/$(date +%Y-%m-%d)

# 生成交易计划
curl -X POST http://localhost:8000/api/plans/generate

# Gemini分析交易计划
curl -X POST http://localhost:8000/api/plans/analyze/gemini
```

---

## 六、AI分析类

### 1. Gemini 深度分析
```bash
# 两只股票对比
curl -X POST http://localhost:8000/api/yaogu/ai/analyze \
  -d '{"codes": ["000001", "000002"], "question": "对比分析这两只股票的优劣"}'

# 交易计划分析
curl -X POST http://localhost:8000/api/gemini/analyze/trading-plan

# 价格区间分析
curl -X POST http://localhost:8000/api/gemini/research/analyze-price-ranges \
  -d '{"codes": ["000001"]}'
```

### 2. DeepSeek 分析
```bash
# 生成交易计划
curl -X POST http://localhost:8000/api/deepseek/plan/generate

# 复盘分析
curl -X POST http://localhost:8000/api/deepseek/review/generate
```

### 3. AnythingLLM 对话
```bash
# 自由对话
curl -X POST http://localhost:8000/api/anythingllm/chat \
  -d '{"message": "分析一下今天的市场情况"}'

# 搜索知识库
curl http://localhost:8000/api/anythingllm/search?q=断板反包
```

### 4. 龙头战法高手问答（NotebookLM - 重要！）

**核心能力**：问战法、问打法、问策略，不问具体股票走势（高手不知道实时行情）

```bash
# 断板反包战法
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "断板反包的最佳入场时机是什么？缩量回踩和放量分歧哪种形态更好？", "wait": true, "timeout": 180}'

# 低吸战法
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "龙头股回踩5日线低吸，需要满足什么条件？换手率多少合适？", "wait": true, "timeout": 180}'

# 缩量情况判断
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "连板股出现缩量加速，是好事还是坏事？后面应该怎么操作？", "wait": true, "timeout": 180}'

# 二进三打法
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "二进三的成功率如何提高？什么样的二板股更容易晋级？", "wait": true, "timeout": 180}'

# 分歧转一致
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "如何判断龙头股的分歧是洗盘还是见顶？分歧转一致有什么特征？", "wait": true, "timeout": 180}'

# 选股对比（问逻辑不问走势）
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "同板块两只龙头，一只是缩量3连板，一只是放量2连板，从龙头战法角度哪只更值得关注？", "wait": true, "timeout": 180}'
```

**正确问法 vs 错误问法**：
| ✅ 正确（问战法） | ❌ 错误（问行情） |
|------------------|------------------|
| 断板反包如何入场？ | 今天XXX涨了多少？ |
| 缩量情况怎么处理？ | XXX明天会涨吗？ |
| 低吸需要什么条件？ | XXX现在能买吗？ |
| 二进三怎么提高成功率？ | XXX走势符合预期吗？ |

**高手知识库包含**：
- 乔帮主（龙头战法核心）
- 佛山无影脚（N字反包）
- 小鳄鱼（主线跟随）
- 赵老哥（人气龙头）
- 金田路（连板战法）
- 炒股养家（格局心法）

---

## 七、标的池管理（编排系统 9002）

```bash
# 读取今日标的池
curl http://localhost:9002/api/pool/{agent_id}

# 读取历史标的池
curl http://localhost:9002/api/pool/{agent_id}/history?limit=7

# 更新标的池
curl -X PUT http://localhost:9002/api/pool/{agent_id} \
  -d '{"data": {...}, "phase": "pre_market"}'

# 合并更新
curl -X PATCH http://localhost:9002/api/pool/{agent_id} \
  -d '{"data": {...}}'
```

---

## 八、思考存储（9001）

```bash
# 记录思考
curl -X POST http://localhost:9001/api/agent/{agent_id}/thought \
  -d '{"type": "analysis", "content": "...", "tags": ["tag1", "tag2"]}'

# 查询思考
curl http://localhost:9001/api/agent/{agent_id}/thoughts?type=analysis

# 更新方法论
curl -X POST http://localhost:9001/api/agent/{agent_id}/methodology \
  -d '{"content": "...", "change_reason": "..."}'
```

---

## 九、推送通知（重要信号时通知用户）

当发现重要交易信号时，可以通过 Telegram 通知用户：

```bash
# 发送 Telegram 通知
curl -X POST http://localhost:8000/api/channel/alert \
  -H "Content-Type: application/json" \
  -d '{
    "title": "🔔 断板信号",
    "message": "中农联合(003042) 突破入场区间上沿，当前价 23.50\n建议: 可分批建仓\n\n📍 来源: duanban_001",
    "level": "warning"
  }'
```

**通知级别**:
- `warning`: ⚠️ 警告 - 一般交易信号
- `info`: ℹ️ 信息 - 状态更新、任务完成
- `critical`: 🚨 严重 - 紧急止损、重大风险

**使用场景**:
1. 竞价发现突破信号 → 立即通知
2. 盘中触及止损价 → 紧急通知
3. 发现重要入场机会 → 通知用户决策
4. 阶段任务完成 → 状态通知

**重要**: 消息中请标注 agent 来源，如 `📍 来源: duanban_001`

---

## 十、技术分析服务（5005 - 重要！）

**服务地址**: `http://localhost:5005`
**功能**: TradingView K线截图分析 + 通达信截图分析 + 龙头战法问答

### 1. TradingView K线分析
```bash
# 提交 TradingView 截图分析任务
curl -X POST http://localhost:5005/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "code": "002009",
    "name": "天奇股份",
    "tasktype": "tradingview",
    "question": "分析这只股票的技术形态和成交量变化"
  }'

# 返回示例: {"code": 0, "task_id": "xxx", "message": "任务已提交"}
```

### 2. 通达信截图分析
```bash
# 上传通达信截图进行分析
curl -X POST http://localhost:5005/upload_image \
  -F "image=@/path/to/screenshot.png" \
  -F "code=002009" \
  -F "name=天奇股份" \
  -F "question=分析K线形态和量能"

# 返回示例: {"code": 0, "task_id": "xxx", "analysis": "..."}
```

### 3. 查询分析结果
```bash
# 获取分析结果
curl http://localhost:5005/analysis/{task_id}

# 获取任务完整状态
curl http://localhost:5005/task_status/{task_id}

# 查看分析管理器状态
curl http://localhost:5005/analysis/manager/status
```

### 4. 龙头战法问答（NotebookLM）
```bash
# 向龙头战法高手请教
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{
    "question": "分析天奇股份、康强电子、金安国纪这三只断板股，哪只更值得关注？",
    "wait": true,
    "timeout": 180
  }'

# 返回示例: {"code": 0, "analysis": "从龙头战法角度...", "notebook_url": "..."}
```

**技术分析使用场景**：
1. **盘后复盘**：对持仓和关注标的进行 K 线分析，判断走势健康度
2. **盘前准备**：分析候选股的技术形态，筛选最优标的
3. **策略验证**：用龙头战法高手验证自己的判断

**并发能力**：支持最多 5 个并发分析任务，每个 Worker 使用独立的 Gemini 账号

---

## 十一、外部研报接口（8086/18080 - 重要！）

**核心能力**：
- 搜索内部 AI 研报库（历史分析、信号记录）
- 查询国际投行研报（JPM、高盛、摩根等）
- 提交深度研报任务（Gemini DeepResearch）

### 1. 内部AI研报搜索 (8086)
```bash
# 搜索研报（按关键词）
curl -s -X POST "http://156.254.5.245:8086/open/mongo/queryData" \
  -H "Content-Type: application/json" \
  -H "x-custom-token: lhjy.653653a5ac6d4f348932d3365abcdeca" \
  -d '{
    "condition": "{\"signalContent\": {\"$regex\": \"关键词\"}}",
    "sort": "{\"createTime\": -1}",
    "page_index": 1,
    "page_count": 10,
    "system_id": 1,
    "schema_name": "research_reports"
  }'
```

### 2. 国际投行研报 (18080)
```bash
# 搜索 JPM/高盛/摩根等研报
curl -s -X POST "http://156.254.5.245:18080/web/search/getBriefReport" \
  -H "Content-Type: application/json" \
  -H "x-custom-token: lhjy.653653a5ac6d4f348932d3365abcdeca" \
  -d '{
    "startDate": "2026-01-01",
    "endDate": "2026-01-30",
    "pageSize": 20,
    "currentPage": 1,
    "keyword": "China"
  }'
```

### 3. 生成新研报任务 (8086)
```bash
# 提交深度研报任务
curl -s -X POST "http://156.254.5.245:8086/open/aiExecutor/chatCompletion" \
  -H "Content-Type: application/json" \
  -H "x-custom-token: lhjy.653653a5ac6d4f348932d3365abcdeca" \
  -d '{
    "type": 2,
    "question": "分析xxx股票的投资价值",
    "deepResearch": 1,
    "priority": 80,
    "userApi": 1
  }'
```

---

## 使用建议

### 各阶段推荐流程

1. **盘前**：先读新闻 → 读昨日标的池 → **查板块和参考股** → 结合研报分析 → 制定计划
2. **竞价**：读竞价数据 → 对比入场区间 → **看板块整体** → 决策 → **有信号立即 Telegram 通知**
3. **盘中**：监控行情 → **检查参考股走势** → **看市场情绪** → 记录信号 → **重要信号 Telegram 通知**
4. **盘后**：复盘总结 → **分析板块表现** → 调用研报分析明日标的 → 问龙头战法高手 → **确定参考股** → 制定明日计划

### 板块分析方法论（重要！）

**核心原则**：不只看个股，要看板块整体

1. **同板块前排互相参照**
   - 例：天奇股份 vs 铁流股份（都是机器人前排）
   - 参考股走强 → 持仓可多拿
   - 参考股走弱 → 警惕补跌风险

2. **板块情绪判断**
   - 板块内多只涨停 → 板块情绪好，个股安全边际高
   - 板块龙头炸板 → 板块可能转弱，注意风险

3. **参考股加入观察列表**
   - 盘后确定明日标的时，同时确定参考股
   - 将参考股加入 watch_list 的 ref_stocks 字段
   - 盘中同时监控标的和参考股

### 核心技能优先级

| 技能 | 端口 | 用途 | 调用时机 |
|------|------|------|----------|
| **龙头战法高手** | 5005 | 策略验证、选股对比 | 决策前必问 |
| **技术分析** | 5005 | K线/成交量分析 | 盘后分析 |
| **研报生成** | 8000 | 深度分析个股 | 盘后为明日准备 |
| **研报库搜索** | 8086 | 查历史分析 | 需要参考时 |
| **Telegram推送** | 8000 | 通知用户 | 重要信号 |

### 重要技能详解

1. **龙头战法高手**（最重要！）
   - 端口：`http://localhost:5005/api/longtoufala`
   - 场景：问战法、问打法、问策略逻辑
   - 高手：乔帮主、佛山、小鳄鱼、赵老哥等大佬的方法论
   - **注意**：问打法不问走势！高手不知道实时行情

2. **技术分析服务**
   - 端口：`http://localhost:5005/tasks`
   - 场景：分析K线形态、成交量变化、技术指标
   - 数据源：TradingView截图 + 通达信截图

3. **研报生成**
   - 端口：`http://localhost:8000/api/gemini/research/save`
   - 场景：盘后为明日关注标的生成深度研报
   - 能力：Gemini DeepResearch 深度分析

4. **研报库搜索**
   - 端口：`http://156.254.5.245:8086`
   - 场景：查询历史分析、搜索相关板块研报
   - 数据：内部AI研报库 + 国际投行研报

5. **Telegram推送**
   - 端口：`http://localhost:8000/api/channel/alert`
   - 场景：发现重要信号时立即通知用户

### 信号通知优先级
- 🚨 止损触发 / 紧急风险 → `level: critical`
- ⚠️ 入场信号 / 突破确认 → `level: warning`
- ℹ️ 阶段完成 / 状态更新 → `level: info`

### 盘后复盘完整流程

```
1. 读取今日数据（标的池、思考、交易）
   ↓
2. 复盘分析（对比预判与实际）
   ↓
3. 问龙头战法高手（复盘请教）
   ↓
4. 确定明日关注标的
   ↓
5. 为每只标的提交研报任务
   ↓
6. 让高手对比分析多只标的
   ↓
7. 搜索研报库（可选）
   ↓
8. 制定明日计划
   ↓
9. 记录总结 + 更新标的池
   ↓
10. Telegram通知用户
```
