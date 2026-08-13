# 晨光奖励系统 · 设计文档

日期：2026-08-13
状态：已获用户批准（称号方案、积分规则、数据方案、入口位置均已确认）

## 1. 背景与目标

为「朝词浅阅」构建**用户闭环 + 情绪价值 + 每日奖励系统**：

- **闭环**：学习行为 → 积分到账 → 攒积分 → 兑换站 → 佩戴称号/使用装饰 → 继续学习
- **情绪价值**：温暖话语随天数递进、每日晨语、里程碑庆祝、积分到账反馈
- **数据方案**：完整后端方案（跨设备同步，与账号体系一致）
- **奖励形式**：积分 + 兑换站
- **积分获取**：每日任务制
- **入口位置**：「归处」页（StudyCenterView）新增 Tab

## 2. 积分获取（每日任务制）

每天 4 项任务，合计约 40 分/天。数据源全部来自**现有表**，无需重复埋点。

| 任务 | 条件 | 积分 |
|---|---|---|
| 每日打卡 | 今日已打卡（`checkin_records`） | +10 |
| 词海拾贝 | 今日背词 ≥ 20 词（`user_daily_stats` 汇总） | +10 |
| 浅读一页 | 今日读完 1 篇（`user_daily_reading.status='done'`） | +15 |
| 小试牛刀 | 今日阅读小测及格（`user_daily_reading.correct >= total/2`） | +5 |

## 3. 里程碑奖励（一次性，触发时庆祝弹窗）

| 连续天数 | 额外奖励 | 庆祝文案 |
|---|---|---|
| 7 天 | +50 分 | 「习惯正在发芽」 |
| 30 天 | +200 分 | 「你已走出一条路」 |
| 100 天 | +800 分 | 「百日铸就晨读人」 |

幂等：以 `reward_point_logs` 中「里程碑」原因 + 对应天数的流水存在性判断是否已发放（唯一约束防重）。

## 4. 兑换站清单

### 称号（玄幻六阶 · 已定稿）

| 积分 | 称号 | 意境 |
|---|---|---|
| 30 | 聚灵 | 聚气于晨，始成灵识 |
| 60 | 启明 | 晨星初启，灵台渐明 |
| 100 | 蕴锋 | 灵气蕴于笔锋 |
| 150 | 承光 | 承晨光以砺道 |
| 220 | 御风 | 驭词而行，御风千里 |
| 350 | 观星 | 观星照词海，问道于朝 |

### 界面装饰（2 款）
| 积分 | 装饰 | 效果 |
|---|---|---|
| 80 | 松风边框 | 打卡页/个人页卡片换松风主题边框 |
| 150 | 晨光氛围 | 归处页顶部加晨光渐变氛围条 |

### 彩蛋学习内容（2 款）
| 积分 | 内容 | 效果 |
|---|---|---|
| 120 | 冷门好词集 | 解锁「冷门好词」隐藏内容页 |
| 200 | 英语习语趣味卡 | 解锁「习语趣味卡」隐藏内容页 |

## 5. 情绪价值实现

1. **温暖话语随天数递进**：打卡/领奖时展示，随连续天数变化
   - 1 天「开始就是最好的进步」→ 3 天「微光正聚」→ 7 天「习惯正在发芽」→ 15 天「渐入佳境」→ 30 天「你已走出一条路」→ 100 天「朝闻道，夕可诵」
2. **每日晨语**：打卡页/奖励页顶部，随日期轮换（本地静态文案库）
3. **里程碑庆祝**：触发时弹庆祝卡（衬线大字 + 晨光渐变 + 轻动画）
4. **积分到账反馈**：+N 分 上浮动效 toast

## 6. 数据模型

新增 4 张表（均含 `tenant_id` 隔离，遵循现有模式；唯一约束命名 `uq_<table>_<cols>`）：

### `reward_user_points` — 积分余额
- `id, tenant_id, user_id, balance(INT), total_earned(INT), updated_at`
- 唯一 `(user_id)`

### `reward_point_logs` — 积分流水
- `id, tenant_id, user_id, amount(INT 可为负), reason(ENUM/VARCHAR), ref_date(Date), note, created_at`
- reason 枚举：`checkin / srs_study / reading / quiz / milestone_7 / milestone_30 / milestone_100 / redeem`
- 唯一 `(user_id, reason, ref_date)` 防重复发放

### `reward_unlocks` — 已解锁奖励
- `id, tenant_id, user_id, item_key(VARCHAR), unlock_date`
- item_key：`title_juling / title_qiming / title_yunfeng / title_chengguang / title_yufeng / title_guanxing / decor_pine_border / decor_sunrise / egg_hidden_words / egg_idiom_cards`
- 唯一 `(user_id, item_key)`

### `reward_settings` — 用户奖励设置
- `id, tenant_id, user_id, equipped_title(item_key), equipped_decor(item_key), updated_at`
- 唯一 `(user_id)`

> 里程碑是否已发放**不落库**，完全由 `reward_point_logs` 中对应 reason 的流水存在性判断（唯一约束防重），避免双源真相。

## 7. 后端接口

挂载 `/english` 前缀，Bearer 认证（UserDep），统一响应 `UnifiedResponse{code, data, message}`：

| 接口 | 方法 | 说明 |
|---|---|---|
| `/english/rewards/overview` | GET | 积分余额 + 今日任务进度 + 已解锁 + 佩戴称号 |
| `/english/rewards/shop` | GET | 兑换站清单（称号/装饰/彩蛋 + 价格 + 是否已解锁） |
| `/english/rewards/redeem` | POST | 兑换（扣积分 + 写 unlocks，幂等防重复） |
| `/english/rewards/equip` | POST | 佩戴/卸下称号（与装饰） |
| `/english/rewards/collect` | POST | **领每日奖励**：结算当日任务积分 + 触发里程碑检查，返回到账明细 + 庆祝事件 |

### 结算机制（闭环核心）

```
打卡成功 / SRS完成 / 一读完成 / 小测及格
        └─► 前端主动调 collect()
                 ├─► 结算当日任务积分（幂等，每日一次）
                 ├─► 检查里程碑（7/30/100 天，一次性）
                 └─► 返回 { earned, milestone, message, quote }
                    → 到账反馈 / 庆祝弹窗
```

### 服务层
新增 `backend/app/services/english/reward_service.py`，复用现有 `CheckinRecord / UserDailyStats / UserDailyReading` 数据源判断任务完成。

### 迁移
新增 Alembic 迁移文件，仿照现有模式（`op.create_table` + 索引 + 唯一约束）。

## 8. 前端

### 新增组件
| 组件 | 说明 |
|---|---|
| `RewardsPane.vue` | 归处页新增 Tab 内容：积分卡（余额+进度）+ 每日任务 4 项 + 兑换站（Tab：称号/装饰/彩蛋） |
| `RewardCelebrationModal.vue` | 里程碑/兑换成功庆祝弹窗 |
| `PointToast.vue` | 积分到账上浮动效 |
| `DailyQuote.vue` | 每日晨语（本地静态文案库，随日期轮换） |
| `RewardShopItem.vue` | 兑换项卡片（价格/已解锁/兑换按钮） |

### 修改
- `StudyCenterView.vue`：`PageTabs` 新增第 4 个 Tab「奖励」，URL `?tab=rewards`
- `CheckinPane.vue`：打卡后触发 `collect()` + 积分到账反馈
- SRS 完成 / 一读完成：完成后触发 `collect()`
- `AppHeader.vue` / `UserArea.vue`：佩戴称号显示在用户名旁

### 样式
遵循晨光森林设计系统 token（`--primary/--sun/--brand-gradient` 等），新增庆祝动画（衬线大字 + 晨光渐变 + 轻缩放/光晕）。

## 9. 范围排除（YAGNI）

- ❌ 不做真实货币/支付/内购
- ❌ 不做积分排行榜（后续可迭代）
- ❌ 装饰仅静态切换（不改动整体主题系统）
- ❌ 彩蛋内容为静态数据页，不做 LLM 生成
- ❌ 不做成就徽章墙（本迭代聚焦积分+兑换站）

## 10. 验收标准

1. 打卡/背词/阅读/小测后调用 `collect()` 能正确结算任务积分，且每日只结算一次
2. 连续 7/30/100 天触发里程碑庆祝与额外积分，只发放一次
3. 兑换扣积分、解锁记录、重复兑换被拒绝
4. 佩戴称号在用户区显示，跨设备登录后同步
5. 归处页「奖励」Tab 展示积分卡、任务进度、兑换站
6. 后端测试（pytest）覆盖结算幂等、里程碑幂等、兑换幂等
