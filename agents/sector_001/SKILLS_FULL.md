# 板块分析专家 - 完整技能手册

## 一、数据查询类

### 1. 热门板块/概念数据
```bash
# 热门概念（含热度、涨幅、龙头股）
curl http://localhost:8000/api/yaogu/sector/hot-concepts
# 返回: [{"name": "CPO概念", "heat_score": 85, "change_pct": 4.5, "leader_stock": "长飞光纤"}...]

# 热门行业
curl http://localhost:8000/api/yaogu/sector/hot-industries

# 龙头概念列表（按标的数量排序）
curl http://localhost:8000/api/yaogu/leader-tags/concepts
# 返回: [{"name": "机器人", "count": 219}, {"name": "半导体", "count": 170}...]

# 概念龙头股
curl http://localhost:8000/api/yaogu/concepts/{concept}/leaders
# 示例: curl http://localhost:8000/api/yaogu/concepts/机器人/leaders

# 概念层级（父子关系）
curl http://localhost:8000/api/yaogu/concepts/hierarchy

# 概念联动
curl http://localhost:8000/api/yaogu/concepts/linkage
```

**重要说明**：
- `high_days_raw` 是**历史战绩**（如"16天12板"），不是今日实时状态
- `lianban_days` 是排序权重，不是实际连板数
- 这些数据用于筛选**有历史战绩的龙头股**进行关注
- 要判断今日是否涨停，需结合实时行情 `/api/market/realtime/{code}`

### 2. 板块分析数据
```bash
# 板块综合分析
curl http://localhost:8000/api/yaogu/sector/analysis

# 新兴板块预警
curl http://localhost:8000/api/yaogu/sector/emerging-alert

# 热门板块研究
curl http://localhost:8000/api/yaogu/sector/research

# 热门板块历史
curl "http://localhost:8000/api/yaogu/sector/history/2026-01-30"
```

### 3. 个股所属板块
```bash
# 个股所属板块
curl http://localhost:8000/api/yaogu/detail/{code}/concept-plates
# 返回: {"reasons": [{"name": "人形机器人", "count": 10}, ...]}

# 个股板块评分
curl http://localhost:8000/api/yaogu/sector/stock-concept-score/{code}

# 个股完整板块评分
curl http://localhost:8000/api/yaogu/sector/stock-full-score/{code}
```

---

## 二、市场数据类

### 1. 市场情绪
```bash
# 市场情绪总结（含多板指数、涨停家数等）
curl http://localhost:8000/api/market/index/summary
# 返回: 情绪分数、多板指数、涨停家数、跌停家数、微盘股指数等

# 历史情绪
curl http://localhost:8000/api/market/index/summary/history
```

### 2. 指数数据
```bash
# 指数实时行情
curl http://localhost:8000/api/market/index/realtime

# 单个指数
curl http://localhost:8000/api/market/index/{code}

# 指数历史
curl http://localhost:8000/api/market/index/history/{code}
```

### 3. 连板数据
```bash
# 连板晋级率（判断市场赚钱效应）
curl http://localhost:8000/api/lianban/index-promotion/$(date +%Y%m%d)

# 连板趋势
curl http://localhost:8000/api/lianban/index-trend

# 连板指数报告
curl http://localhost:8000/api/lianban/index-report/$(date +%Y%m%d)
```

### 4. 个股实时行情
```bash
# 单只股票
curl http://localhost:8000/api/market/realtime/000856

# 多只股票（逗号分隔）
curl http://localhost:8000/api/market/realtime/000856,002931,300124
```

---

## 三、妖股和优选标的

### 1. 妖股榜
```bash
# 妖股列表（注意：yaogu-list 是正确路由）
curl http://localhost:8000/api/yaogu/yaogu-list
# 返回: 99条妖股数据，含 high_days（历史战绩）、yaogu_score 等

# 妖股详情
curl http://localhost:8000/api/yaogu/{code}

# 妖股买入区间
curl http://localhost:8000/api/yaogu/trade-zones/{code}
```

**重要说明**：
- 妖股榜的 `high_days` 是**历史最高战绩**，不是当前状态
- 用于发现有妖股潜质的标的进行**跟踪关注**
- 需结合实时行情判断当前是否在连板中

### 2. 优选标的
```bash
# 优选标的列表
curl http://localhost:8000/api/selected-stocks

# 推荐标的
curl http://localhost:8000/api/selected-stocks/recommend

# 带板块评分的优选标的
curl http://localhost:8000/api/screening/selected/with-sector-scores

# 热门板块中的优选标的
curl http://localhost:8000/api/yaogu/sector/hot-concept-selected-stocks
```

---

## 四、研报类

### 1. Gemini DeepResearch（深度调研 - 重要！）

**核心能力**：板块调研，从板块找机会

```bash
# 热门板块分析
curl -X POST http://localhost:8000/api/gemini/research/save \
  -H "Content-Type: application/json" \
  -d '{
    "date": "'"$(date +%Y-%m-%d)"'",
    "prompt": "分析A股当前热门板块：\n1)哪些板块近期资金持续流入\n2)哪些板块龙头股走势健康，有持续性\n3)哪些板块有政策或事件催化\n4)热门板块的轮动规律\n5)热门板块中值得关注的标的",
    "task_type": "hot_sector_analysis",
    "priority": 85,
    "auto_submit": true
  }'

# 冷门板块机会
curl -X POST http://localhost:8000/api/gemini/research/save \
  -H "Content-Type: application/json" \
  -d '{
    "date": "'"$(date +%Y-%m-%d)"'",
    "prompt": "挖掘A股冷门板块机会：\n1)哪些板块近期调整充分，可能反转\n2)哪些板块估值处于历史低位\n3)哪些冷门板块有潜在催化剂\n4)冷门板块中被低估的龙头股\n5)风险提示和入场时机判断",
    "task_type": "cold_sector_analysis",
    "priority": 80,
    "auto_submit": true
  }'

# 板块轮动分析
curl -X POST http://localhost:8000/api/gemini/research/save \
  -H "Content-Type: application/json" \
  -d '{
    "date": "'"$(date +%Y-%m-%d)"'",
    "prompt": "分析A股板块轮动规律：\n1)今日强势板块明日是否延续\n2)哪些板块可能接力成为新热点\n3)板块轮动的周期规律\n4)如何提前发现板块启动信号\n5)板块轮动中的交易策略",
    "task_type": "sector_rotation",
    "priority": 85,
    "auto_submit": true
  }'

# 查询研报任务
curl http://localhost:8000/api/gemini/research/tasks

# 获取研报结果
curl http://localhost:8000/api/gemini/research/report/{task_id}
```

### 2. 外部研报接口（8086）
```bash
# 搜索板块相关研报
curl -s -X POST "http://156.254.5.245:8086/open/mongo/queryData" \
  -H "Content-Type: application/json" \
  -H "x-custom-token: lhjy.653653a5ac6d4f348932d3365abcdeca" \
  -d '{
    "condition": "{\"signalContent\": {\"$regex\": \"机器人\"}}",
    "sort": "{\"createTime\": -1}",
    "page_index": 1,
    "page_count": 10,
    "system_id": 1,
    "schema_name": "research_reports"
  }'
```

---

## 五、新闻分析类

### 1. 新闻数据
```bash
# 新闻列表
curl http://localhost:8000/api/news/list?limit=30

# 最新快讯
curl http://localhost:8000/api/yaogu/news/latest?limit=20

# 个股新闻
curl http://localhost:8000/api/yaogu/news/{code}
```

### 2. 热门概念/关键词
```bash
# 新闻热门概念
curl http://localhost:8000/api/yaogu/news/hot-concepts

# 新闻热门关键词
curl http://localhost:8000/api/yaogu/news/hot-keywords
```

### 3. 龙头热度
```bash
# 检查概念龙头是否有新闻热度
curl http://localhost:8000/api/yaogu/news/leader-hot-check/{code}

# 扫描所有龙头热度
curl http://localhost:8000/api/yaogu/news/scan-leaders-hot

# 概念龙头（结合新闻）
curl http://localhost:8000/api/yaogu/news/concept-leaders/{concept}
```

### 4. 新闻摘要
```bash
# 生成新闻摘要
curl -X POST http://localhost:8000/api/news/summary/generate

# 获取某日新闻摘要
curl http://localhost:8000/api/news/summary/$(date +%Y-%m-%d)

# 摘要历史
curl http://localhost:8000/api/news/summary/history
```

---

## 六、AI分析类

### 1. 龙头战法高手问答（NotebookLM - 重要！）

**核心能力**：问战法、问板块分析方法，不问具体股票走势

```bash
# 板块持续性判断
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "如何判断一个板块是否有持续性？龙头股和板块指数应该怎么配合看？", "wait": true, "timeout": 180}'

# 板块龙头见顶信号
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "板块龙头连板到高位（如10板以上）后，板块还能继续吗？如何判断板块是否见顶？", "wait": true, "timeout": 180}'

# 板块轮动规律
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "高位板块调整时，如何判断哪个低位板块会接力？板块轮动有什么规律？", "wait": true, "timeout": 180}'

# 冷门板块启动信号
curl -X POST http://localhost:5005/api/longtoufala \
  -H "Content-Type: application/json" \
  -d '{"question": "冷门板块调整充分后，有什么启动信号？如何判断是真启动还是假突破？", "wait": true, "timeout": 180}'
```

**正确问法 vs 错误问法**：
| ✅ 正确（问板块方法论） | ❌ 错误（问行情） |
|----------------------|------------------|
| 板块如何判断持续性？ | 机器人板块今天涨了多少？ |
| 龙头断板后板块会怎样？ | XXX板块明天会涨吗？ |
| 冷门板块启动信号是什么？ | 地产板块现在能买吗？ |

### 2. 技术分析服务（5005）

```bash
# 通达信板块指数截图分析
curl -X POST http://localhost:5005/upload_image \
  -F "image=@/path/to/sector_index.png" \
  -F "code=BK0493" \
  -F "name=机器人板块指数" \
  -F "question=分析这个板块指数的技术形态，判断板块强弱和后续走势"

# 查询分析结果
curl http://localhost:5005/analysis/{task_id}

# 查看分析管理器状态
curl http://localhost:5005/analysis/manager/status
```

---

## 七、标的池管理（9002）

```bash
# 读取今日板块分析结果
curl http://localhost:9002/api/pool/sector_001

# 读取历史分析
curl http://localhost:9002/api/pool/sector_001/history?limit=7

# 更新板块分析（覆盖）
curl -X PUT http://localhost:9002/api/pool/sector_001 \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "date": "'"$(date +%Y-%m-%d)"'",
      "market_sentiment": {"score": 65, "level": "中性"},
      "hot_sectors": [
        {"name": "机器人", "leaders": ["锋龙股份", "冀东装备"], "strength": "强", "sustainability": "高"}
      ],
      "cold_sectors": [
        {"name": "地产", "status": "调整中", "potential": "待观察"}
      ],
      "recommendations": [
        {"code": "002931", "name": "锋龙股份", "sector": "机器人", "reason": "板块龙头"}
      ]
    },
    "phase": "pre_market"
  }'

# 合并更新（保留原有数据）
curl -X PATCH http://localhost:9002/api/pool/sector_001 \
  -H "Content-Type: application/json" \
  -d '{"data": {...}}'
```

---

## 八、思考存储（9001）

```bash
# 记录板块分析思考
curl -X POST http://localhost:9001/api/agent/agent_sector/thought \
  -H "Content-Type: application/json" \
  -d '{"type": "sector_analysis", "content": "今日热门板块：机器人、半导体...", "tags": ["sector","analysis","'"$(date +%Y%m%d)"'"]}'

# 查询历史思考
curl http://localhost:9001/api/agent/agent_sector/thoughts?type=sector_analysis&limit=10

# 按标签查询
curl "http://localhost:9001/api/agent/agent_sector/thoughts?tags=pre_market&limit=5"
```

---

## 九、推送通知

```bash
# 发送 Telegram 通知
curl -X POST http://localhost:8000/api/channel/alert \
  -H "Content-Type: application/json" \
  -d '{
    "title": "🔥 板块机会",
    "message": "热门板块: 机器人、半导体\n龙头股: 锋龙股份(历史16天12板)\n冷门机会: 地产调整充分\n\n📍 来源: sector_001",
    "level": "info"
  }'
```

**通知级别**:
- `warning`: ⚠️ 警告 - 板块异动信号
- `info`: ℹ️ 信息 - 状态更新、任务完成
- `critical`: 🚨 严重 - 板块龙头炸板、重大风险

---

## 使用建议

### 各阶段推荐流程

1. **盘前**：
   - 读取昨日分析（标的池 + 思考）
   - 获取市场情绪和板块数据
   - 提交板块深度调研任务
   - 确定今日重点板块和推荐标的
   - 记录思考 + 更新标的池 + 推送通知

2. **盘中**：
   - 读取盘前分析
   - 监控热门板块龙头走势
   - 发现板块异动 → 分析原因
   - 重要信号 → Telegram 通知
   - 记录盘中观察

3. **盘后**：
   - 读取全天分析（标的池 + 思考）
   - 总结板块表现（预判 vs 实际）
   - 提交板块轮动调研
   - 挖掘冷门板块机会
   - 问龙头战法高手
   - 确定明日重点板块
   - 记录总结 + 更新标的池 + 推送通知

### 核心方法论

#### 1. 热门板块判断标准
- 龙头股连板高度（3板以上）
- 板块内涨停家数（5只以上）
- 资金持续流入
- 有明确催化剂（政策/事件）

#### 2. 冷门板块机会识别
- 调整时间充分（1-3个月）
- 龙头股企稳不再创新低
- 有潜在催化剂（政策/业绩）
- 估值处于历史低位

#### 3. 板块轮动规律
- 高位板块调整 → 低位板块补涨
- 主线板块回调 → 支线板块接力
- 大盘股轮动 → 小盘股跟随

#### 4. 从板块找标的
- 选择板块龙头（高度最高）
- 选择板块前排（跟随龙头）
- 避免板块杂毛（容易被抛弃）

### 核心技能优先级

| 技能 | 端口 | 用途 | 调用时机 |
|------|------|------|----------|
| **DeepResearch** | 8000 | 板块深度调研 | 盘前/盘后必做 |
| **龙头战法高手** | 5005 | 板块方法论验证 | 决策前可问 |
| **热门板块API** | 8000 | 实时板块数据 | 随时查询 |
| **研报库搜索** | 8086 | 查历史分析 | 需要参考时 |
| **Telegram推送** | 8000 | 通知用户 | 重要信号 |

### 链式思考流程

```
盘前分析 (8:30-9:15)
├── 读取昨日标的池 + 复盘思考
├── 分析今日板块机会
├── 记录思考 → 9001
└── 更新标的池 → 9002
       ↓
盘后总结 (15:30+)
├── 读取盘前分析（标的池 + 思考）
├── 复盘板块表现
├── 确定明日方向
├── 记录总结 → 9001
└── 更新标的池（含明日计划）→ 9002
```

---

## 九、AkShare 板块K线分析（推荐！）

### 获取板块实时数据
```python
import akshare as ak

# 概念板块列表（含今日涨跌、领涨股）
df = ak.stock_board_concept_name_em()
# 返回: 板块名称, 涨跌幅, 领涨股票, 领涨涨跌幅, 上涨家数, 下跌家数...

# 筛选热门板块
hot = df.head(15)[['板块名称', '涨跌幅', '领涨股票', '领涨涨跌幅']]
```

### 获取板块历史K线（技术分析）
```python
# 获取单个板块历史K线
df = ak.stock_board_concept_hist_em(
    symbol="CPO概念",  # 板块名称
    period="daily",    # daily/weekly/monthly
    start_date="20240101",
    end_date="20260131"
)
# 返回: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率

# 计算均线
df['MA5'] = df['收盘'].rolling(5).mean()
df['MA10'] = df['收盘'].rolling(10).mean()
df['MA20'] = df['收盘'].rolling(20).mean()

# 判断趋势
latest = df.iloc[-1]
if latest['收盘'] > latest['MA5'] > latest['MA10']:
    trend = "🟢 多头排列"
elif latest['收盘'] < latest['MA5'] < latest['MA10']:
    trend = "🔴 空头排列"
else:
    trend = "🟡 震荡整理"
```

### 批量分析多个板块
```python
boards = ["CPO概念", "机器人执行器", "半导体概念", "存储芯片", "AI芯片"]
for board in boards:
    df = ak.stock_board_concept_hist_em(symbol=board, period="daily")
    # 分析逻辑...
```

**优势**：不依赖截图服务，直接获取数据进行分析

---

## 十、ClickHouse 数据表（高级查询）

### 板块/概念数据表

| 表名 | 数据源 | 内容 | 板块数量 | 有代码 |
|------|--------|------|----------|--------|
| `stock_block_em` | 东财 | 行业-成分股 | 85个行业 | ✅ BKxxxx |
| `stock_block` | 东财 | 概念-成分股 | 269个概念 | ❌ 只有名称 |
| `bankuai_index_em` | 东财 | 板块指数K线 | 100概念+86行业 | ✅ BKxxxx |
| `stock_block_ths` | 同花顺 | 板块-成分股 | 994个 | ✅ 886xxx.TI |
| `concept_heat_daily` | 自计算 | 概念热度 | ~200个 | ❌ 只有名称 |

### 常用查询示例

```sql
-- 1. 查询概念板块代码
SELECT DISTINCT block_code, block_name
FROM default.bankuai_index_em
WHERE block_type = 'concept'
  AND block_name LIKE '%人工智能%'

-- 2. 查询板块成分股
SELECT stock_code, stock_name
FROM default.stock_block
WHERE block_name = 'CPO概念'

-- 3. 查询板块历史K线
SELECT date, close, pct_change
FROM default.bankuai_index_em
WHERE block_name = '人工智能'
ORDER BY date DESC
LIMIT 30
```

### 注意事项
- `stock_block` 表没有板块代码，只有概念名称
- 概念数据不完整：`bankuai_index_em` 只有100个概念，但 `stock_block` 有269个
