# 武汉晚霞预报推送

只在高分（值得拍）的日子提醒你，其他日子保持安静。每 6 小时检查一次数据，日落前会额外盯一次。

## 两套运行方式

| 方式 | 触发 | 何时用 |
|---|---|---|
| **GitHub Actions**（推荐，24h 可靠） | 云端定时，不依赖你的电脑 | 日常自动运行 |
| 本机 Windows 任务计划 | 需登录且不休眠 | 备用 / 手动调试 |

> **同一时间只启用一套**。两套都开着会各推一条，因为状态文件不互通（云端是仓库里的 `state.json`，本机是本地的）。

## 推送格式

标题（微信通知栏里那一行）：

```
武汉晚霞 21分·平淡
```

正文（markdown，每行末尾都补了两个空格强制换行，避免渲染时被黏成一段。**没有标题行**，因为通知栏标题已经显示了城市和分数）：

```
**2026-10-04** ｜ 日落 **18:04** ｜ 天气 阴

**综合评分 21/100 — 平淡**
观赏概率 92%（极易观测）

**能见度** 10.38 km ｜ **置信度** medium
**出动** 建议 17:35 到达，18:34 后可撤
**蓝调** 18:21–18:40（灰蓝有限，30 分）

<sub>数据：glowsunset.cn · Open-Meteo 三模式低云一致</sub>
```

页脚那半句是多模式校验的压缩版，四种取值：

| 页脚显示 | 含义 |
|---|---|
| `Open-Meteo 三模式低云一致` | ECMWF / GFS / CMA 三家低云量相差 < 25 个百分点，预测可信 |
| `Open-Meteo 三模式低云基本一致` | 相差 25 ~ 40 个百分点，大致可信 |
| `⚠️ Open-Meteo 三模式低云分歧大` | 相差 ≥ 40 个百分点，**这次预测本身不可靠，出门前掂量一下** |
| `Open-Meteo 三模式校验缺失` | 没取到校验数据 |

带具体数值的详细版永远写在 `logs/sunset_glow.log` 里，推送里只放上面这句结论。

格式定义在 `sunset_glow.py` 的 `build_markdown()` 函数：正文是一个 `lines` 列表，一个元素一行，最后用 `harden()` 补行尾空格后拼接。改文案就是改这个列表。

预览改动的效果（不会真发消息）：

```bash
python sunset_glow.py --mode test --dry-run
```

## Token 存放（重要：不要写进 config.json）

**token 绝不写在 `config.json` 里**，因为那个文件要提交到仓库。按运行方式来选：

| 运行方式 | token 放哪 |
|---|---|
| GitHub Actions | 仓库 **Settings → Secrets and variables → Actions → New repository secret**，名称 `PUSHPLUS_TOKEN` |
| 本机手动运行 | 项目目录下建 `local_secrets.json`（已 gitignore，不会被提交） |

`local_secrets.json` 格式：

```json
{
  "PUSHPLUS_TOKEN": "你的消息token"
}
```

取 token 的优先级是：**环境变量 → `local_secrets.json` → `config.json`**。所以在 GitHub 上由 Secrets 注入的环境变量永远优先，本机则自动落到 `local_secrets.json`。

推送服务二选一，推荐 PushPlus（免费额度 200 条/天，比 Server酱 的 5 条/天宽松）：

- **PushPlus**：微信扫码登录 <https://www.pushplus.plus/>，在「一对一推送」页创建一个 **消息token**，`provider` 填 `pushplus`
- **Server酱**：微信扫码登录 <https://sct.ftqq.com/>，复制 SendKey，`provider` 填 `serverchan`，环境变量名用 `SERVERCHAN_TOKEN`

> **为什么用消息token而不是用户token？** 官方文档《用户token和消息token有什么区别》原文：
> - 「用户token和消息token均可以用于发送消息，填写在"token"参数上。」——本脚本用的 `/send` 接口两者都支持。
> - 「消息token可创建多个，可自行标识使用的场景，方便管理和维护。**主要用在第三方开发的脚本、程序或系统上。**」——正是本脚本的场景。
> - 「用户token代表具体您是哪个用户，有且仅有一个，**无法删除**。」——而消息token可以随时删除重建，万一泄露可立刻撤销，不用换账号。
>
> 注：文档里另有一条「开放接口调用需要使用用户token，不支持消息token」——那指的是另一套接口（[开放接口文档](https://www.pushplus.plus/doc/guide/openApi.html)），本脚本用的是消息接口 `/send`，不受此限制。

## 常用命令

```bash
python sunset_glow.py --mode digest    # 常规检查（每 6 小时的任务用的就是这个）
python sunset_glow.py --mode alert     # 日落前加推检查
python sunset_glow.py --mode test      # 立刻发一条真实数据的测试推送
python sunset_glow.py --mode digest --dry-run   # 只打印不发送，用来验证判定逻辑
python sunset_glow.py --mode digest --force     # 忽略"今日已推送"去重
```

也可以直接双击 `run.bat`（默认走 digest）。

## 部署到 GitHub Actions（24 小时运行）

本机的 Windows 任务计划有个硬伤：任务的登录类型是 `Interactive`，**只有你登录着 Windows 时才会触发**。关机、注销、系统更新后停在登录界面，都会静默停摆。GitHub Actions 跑在云端，与你电脑无关。

### 成本

| 项 | 数字 |
|---|---|
| 运行次数 | 常规 4 次/天 + 加推 7 次/天 = 11 次/天 ≈ 330 次/月 |
| 计费 | 按分钟计，**每次最低 1 分钟**（哪怕只跑 5 秒） |
| 月消耗 | ≈ 330 分钟 |
| 私有仓库免费额度 | **2,000 分钟/月**，占用约 17% |

### 两个 workflow

| 文件 | 频率 | 模式 |
|---|---|---|
| `.github/workflows/digest.yml` | 每 6 小时（cron `12 */6 * * *`） | `--mode digest` |
| `.github/workflows/alert.yml` | 每天 14:00–20:00 每小时（`7 14-20 * * *`） | `--mode alert` |

cron 都用 `Asia/Shanghai` 时区，不需要自己换算 UTC。

**为什么 cron 写 `:12` 和 `:07`，而不是整点？** GitHub 官方文档明确说 `The schedule event can be delayed during periods of high loads`，并建议 `schedule your workflow to run at a different time of the hour`。整点是全球最拥堵的时刻，错开能降低延迟概率。

### 状态回写

去重状态存在 `state.json`，但 GitHub runner 每次都是全新环境、跑完即销毁，所以每个 workflow 最后都有一步把 `state.json` 提交回仓库。这一步同时让仓库保持活跃，规避"60 天无活动自动禁用 scheduled workflow"的政策（该政策官方原文针对公开仓库）。

两个 workflow 共用 `concurrency: sunset-glow` 互斥组，避免同时提交冲突。

### 首次部署步骤

1. 建一个**私有**仓库，推上本项目
2. 仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加 `PUSHPLUS_TOKEN`
3. 手动触发 `连通性测试` workflow，确认 runner 能访问目标站点（**这一步很关键，见下**）
4. 手动触发 `晚霞预报-常规检查`，确认微信收到推送
5. 确认无误后，**停掉本机定时任务**，避免重复推送

### ⚠️ 部署前必须验证的跨境网络问题

`glowsunset.cn` 和 `www.pushplus.plus` 都托管在**阿里云国内节点且没有走 CDN**（实测分别解析到 8.130.45.255 北京、121.40.246.120 杭州），而 GitHub 的 runner 在美国。跨境直连国内源站可能慢、也可能被 WAF 拦。

所以 `.github/workflows/connectivity-test.yml` 是**部署的第一道关卡**：它只做只读探测（不会真的发消息），打印两个站点的 HTTP 状态码、耗时和接口返回摘要。跑通了再启用正式任务；如果被拦，就得换方案（比如保留本机运行）。

## 本机定时任务（备用）

| 任务名 | 频率 | 说明 |
|---|---|---|
| `SunsetGlow_Digest` | 每 6 小时（06:12 / 12:12 / 18:12 / 00:12） | 常规检查，只在今天达到高分线时推送 |
| `SunsetGlow_PreSunset` | 每天 14:00–20:00 每小时 | 日落前窗口检查，达标时加推一条提醒你出门；每天最多一条 |

⚠️ 这两个任务的登录类型是 `Interactive`（仅登录时运行）。要和 GitHub Actions 二选一，不要同时开。

管理命令（管理员或普通权限均可）：

```powershell
Get-ScheduledTask -TaskName 'SunsetGlow_*'                    # 查看状态
Disable-ScheduledTask -TaskName 'SunsetGlow_Digest'           # 暂停
Enable-ScheduledTask -TaskName 'SunsetGlow_Digest'            # 恢复
Start-ScheduledTask -TaskName 'SunsetGlow_Digest'             # 立即跑一次
Unregister-ScheduledTask -TaskName 'SunsetGlow_Digest' -Confirm:$false   # 删除
```

重新注册（改了时间或路径后）：`powershell -ExecutionPolicy Bypass -File E:\Sunset\register_tasks.ps1`

## 推送规则

推送条件全部满足才会发：

1. **今天**综合评分 ≥ `push_min_quality`（默认 60）
2. 还没到日落前 30 分钟（日落后再提醒就没意义了）
3. 当前时间在 `push_window_start` ~ `push_window_end`（默认 05:00–21:00，深夜不打扰）
4. 当天这个类型的事件还没推送过（去重记录在 `state.json`）

另外两种情况会额外触发：

- **临场加推**：日落前 4 小时到前 45 分钟之间，若当天评分仍 ≥ 60，加推一条（`alert` 模式）
- **明日预告**：未来第一个预报日的评分 ≥ `advance_fire_quality`（默认 85，绝美级）时提前一天预告。不想要就把它关掉：

```json
"advanced": { "announce_advance_fire_day": false }
```

## 配置说明（config.json）

| 字段 | 含义 |
|---|---|
| `location.spot` | glowsunset 的地点标识，武汉是 `wuhan`。其他城市改成对应英文名（如 `hangzhou`、`shenzhen`） |
| `location.latitude/longitude` | 用于 Open-Meteo 交叉校验的坐标 |
| `thresholds.push_min_quality` | 推送门槛，60 = 网站定义的"很棒"级 |
| `thresholds.advance_fire_quality` | 提前预告门槛，85 = "绝美"级 |
| `schedule.push_window_*` | 允许推送的时间段 |
| `schedule.alert_*` | 日落前加推的时间窗口 |
| `advanced.crosscheck_disagreement_spread` | 三个数值模式低云相差多少个百分点算"模型分歧"（默认 40） |

## 数据来源

- **glowsunset.cn**（主）——`https://glowsunset.cn/api/spot/{spot}`，返回评分、点评、蓝调时段、建议到达时间、机位、摄影参数。该接口没有公开文档，是网站前端在调用的；站方未来若改动接口，脚本会记录失败日志并安静退出，不会发错误推送。
- **Open-Meteo 多模式**（交叉校验）——对比 ECMWF / GFS / 中国气象局 CMA 三套数值预报的低云量，判断这次预测可不可信。结论压缩成半句挂在推送页脚（见上文"页脚那半句"表），带具体数值的详细版写在 `logs/sunset_glow.log` 和 `state.json` 的 `last_crosscheck` 字段里。

注意一个实测坑：glowsunset 的 `probability`（观赏概率）和 `quality`（综合评分）会背离，比如会出现 `probability 92%「极易观测」` 但 `quality 21`、点评写「阴天休战」的情况——因为概率说的是"光线通不通"，评分说的是"整体好不好看"。所以本脚本以 `quality` 为唯一判定依据，`probability` 只作展示。

## 文件说明

| 文件 | 作用 |
|---|---|
| `sunset_glow.py` | 主脚本 |
| `config.json` | 配置（位置、阈值、渠道 token） |
| `state.json` | 去重状态与最近一次校验结果 |
| `logs/sunset_glow.log` | 运行日志（每次运行都记，方便回溯"为什么没推"） |
| `run.bat` | 手动运行入口 |
| `register_tasks.ps1` | 重新注册定时任务 |
