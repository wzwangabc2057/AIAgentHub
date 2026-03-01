# 规则部署 API 文档

> **服务地址**: http://localhost:8769
> **API 文档**: http://localhost:8769/docs

---

## 核心 API

### 1. 批量部署规则 (推荐使用)

```bash
POST http://localhost:8769/rules/deploy
Content-Type: application/json

{
    "stocks": [
        {
            "code": "601615",
            "name": "明阳智能",
            "board_count": 3,
            "rule_type": "breakout",
            "breakout_price": 23.82,
            "amount": 50000
        },
        {
            "code": "002201",
            "name": "九鼎新材",
            "board_count": 5,
            "rule_type": "low_suction",
            "turnover_rate_max": 3,
            "amount": 50000
        }
    ],
    "machine": "m1",
    "submit_to_5002": false
}
```

**StockRule 字段说明：**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| code | string | ✅ | - | 股票代码 |
| name | string | ✅ | - | 股票名称 |
| board_count | int | ❌ | 0 | 连板数 |
| rule_type | string | ❌ | "breakout" | 规则类型: breakout/low_suction |
| breakout_price | number | ❌ | null | 突破价格 |
| use_high_5d | bool | ❌ | true | 使用5日最高价作为突破价 |
| amount | number | ❌ | 50000 | 买入金额 |
| volume_ratio_min | number | ❌ | 1.0 | 最小量比 |
| turnover_rate_max | number | ❌ | 3.0 | 最大换手率(低吸用) |
| stop_loss_pct | number | ❌ | -5 | 止损百分比 |
| take_profit_pct | number | ❌ | 8 | 止盈百分比 |

---

### 2. 快捷部署突破规则

```bash
POST http://localhost:8769/deploy/breakout?code=601615&name=明阳智能&breakout_price=23.82&amount=50000&submit=true

# 参数说明:
# - code: 股票代码 (必填)
# - name: 股票名称 (必填)
# - breakout_price: 突破价格 (可选，默认用5日最高)
# - use_high_5d: 使用5日最高价 (默认true)
# - board_count: 连板数 (默认0)
# - amount: 买入金额 (默认50000)
# - machine: 目标机器 (默认m1)
# - submit: 是否立即下发到5002 (默认false)
```

---

### 3. 快捷部署低吸规则

```bash
POST http://localhost:8769/deploy/low-suction?code=002201&name=九鼎新材&turnover_rate_max=3&amount=50000&submit=true

# 参数说明:
# - code: 股票代码 (必填)
# - name: 股票名称 (必填)
# - target_price: 目标价格 (可选)
# - turnover_rate_max: 最大换手率 (默认3.0)
# - amount: 买入金额 (默认50000)
# - machine: 目标机器 (默认m1)
# - submit: 是否立即下发到5002 (默认false)
```

---

### 4. 查看规则

```bash
# 查看所有规则
GET http://localhost:8769/rules

# 查看单条规则
GET http://localhost:8769/rules/{rule_id}
```

---

### 5. 删除规则

```bash
# 删除指定规则
DELETE http://localhost:8769/rules/{rule_id}

# 清空某股票的所有规则
DELETE http://localhost:8769/rules?code=601615

# 清空所有规则
DELETE http://localhost:8769/rules
```

---

### 6. 下发规则到交易系统 (5002)

```bash
POST http://localhost:8769/rules/submit
Content-Type: application/json

{
    "machine": "m1",
    "rule_ids": ["rule_id_1", "rule_id_2"]  // 可选，为空则下发所有
}
```

---

### 7. 取消规则

```bash
POST http://localhost:8769/rules/cancel
Content-Type: application/json

{
    "rule_id": "rule_id_to_cancel"
}
```

---

### 8. 更新突破价格

```bash
POST http://localhost:8769/rules/update-price?code=601615&price=24.50
```

---

### 9. 盘前检查规则

```bash
POST http://localhost:8769/rules/check
```

---

### 10. 保存规则到文件

```bash
POST http://localhost:8769/rules/save
```

---

## 断板反包专家使用示例

### 场景1: 部署所有待分析股票

```bash
curl -X POST http://localhost:8769/rules/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "stocks": [
        {"code": "601615", "name": "明阳智能", "board_count": 3, "rule_type": "breakout", "breakout_price": 23.82, "amount": 50000},
        {"code": "002201", "name": "九鼎新材", "board_count": 5, "rule_type": "low_suction", "turnover_rate_max": 3, "amount": 50000},
        {"code": "001288", "name": "运机集团", "board_count": 2, "rule_type": "breakout", "use_high_5d": true, "amount": 37500},
        {"code": "600986", "name": "浙文互联", "board_count": 3, "rule_type": "breakout", "use_high_5d": true, "amount": 50000},
        {"code": "688323", "name": "瑞华泰", "board_count": 2, "rule_type": "breakout", "use_high_5d": true, "amount": 37500}
    ],
    "machine": "m1",
    "submit_to_5002": false
}'
```

### 场景2: 快速部署单只突破规则

```bash
curl -X POST "http://localhost:8769/deploy/breakout?code=600986&name=浙文互联&board_count=3&amount=50000&submit=false"
```

### 场景3: 快速部署龙头低吸规则

```bash
curl -X POST "http://localhost:8769/deploy/low-suction?code=002201&name=九鼎新材&turnover_rate_max=3&amount=50000&submit=false"
```

### 场景4: 检查并下发到交易系统

```bash
# 1. 盘前检查
curl -X POST http://localhost:8769/rules/check

# 2. 下发到5002
curl -X POST http://localhost:8769/rules/submit \
  -H "Content-Type: application/json" \
  -d '{"machine": "m1"}'
```

---

## 分级打法与规则类型对应

| 连板数 | 打法 | rule_type | 关键参数 |
|--------|------|-----------|----------|
| 1板 | 站上涨停价 | breakout | breakout_price=涨停价 |
| 2板 | 超前高 | breakout | use_high_5d=true |
| 3板+ | 突破/低吸 | breakout | use_high_5d=true |
| 龙头 | 极致缩量 | low_suction | turnover_rate_max=3 |

---

## 注意事项

1. **submit_to_5002=false**: 先部署规则，检查无误后再手动下发
2. **use_high_5d=true**: 自动获取5日最高价作为突破价
3. **机器选择**: m1 是主要交易机器
4. **止损止盈**: 规则自动包含止损(-5%)和止盈(8%)
