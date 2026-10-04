# 武汉晚霞预报推送

只在高分（值得拍）的日子提醒你，其他日子保持安静。每 6 小时检查一次数据，日落前会额外盯一次。

## 当前状态

- 位置：武汉（黄鹤楼 / 长江大桥，`/api/spot/wuhan` 对应的机位）
- 高分线：综合评分 **≥ 60**（网站官方分级：≥85 绝美 / ≥60 很棒 / ≥30 不错 / ≥1 平淡 / 0 无望）
- 推送渠道：**只走微信**（PushPlus）。桌面弹窗代码已移除，不再需要
- 定时任务：已注册（见"定时任务"节）

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

## 微信推送配置（已配置完成）

二选一，推荐 PushPlus（免费额度 200 条/天，比 Server酱 的 5 条/天宽松）。

**方案 A：PushPlus**
1. 手机微信扫码登录 <https://www.pushplus.plus/>
2. 在「一对一推送」页面创建并复制一个 **消息token**（不要用用户token，原因见下方说明）
3. 打开 `E:\Sunset\config.json`，把 `channels.wechat` 改成：

```json
"wechat": {
  "enabled": true,
  "provider": "pushplus",
  "token": "这里粘贴你的消息token"
}
```

> **为什么用消息token而不是用户token？** 官方文档《用户token和消息token有什么区别》原文：
> - 「用户token和消息token均可以用于发送消息，填写在"token"参数上。」——本脚本用的 `/send` 接口两者都支持。
> - 「消息token可创建多个，可自行标识使用的场景，方便管理和维护。**主要用在第三方开发的脚本、程序或系统上。**」——正是本脚本的场景。
> - 「用户token代表具体您是哪个用户，有且仅有一个，**无法删除**。」——而消息token可以随时删除重建。
>
> 脚本会把 token 明文保存在 `config.json` 里，用可删除可轮换的消息token更安全，也方便你按脚本命名（比如起名「晚霞预报」），以后一眼看出是哪个程序在用、要撤销时也只影响这一个。
>
> 注：文档里另有一条「开放接口调用需要使用用户token，不支持消息token」——那指的是另一套接口（[开放接口文档](https://www.pushplus.plus/doc/guide/openApi.html)），本脚本用的是消息接口 `/send`，不受此限制。

**方案 B：Server酱**
1. 微信扫码登录 <https://sct.ftqq.com/>，复制 SendKey
2. `config.json` 里改成 `"provider": "serverchan"`，token 填 SendKey

改完之后跑一次测试，确认微信能收到：

```bash
cd /d E:\Sunset
python sunset_glow.py --mode test
```

## 常用命令

```bash
python sunset_glow.py --mode digest    # 常规检查（每 6 小时的任务用的就是这个）
python sunset_glow.py --mode alert     # 日落前加推检查
python sunset_glow.py --mode test      # 立刻发一条真实数据的测试推送
python sunset_glow.py --mode digest --dry-run   # 只打印不发送，用来验证判定逻辑
python sunset_glow.py --mode digest --force     # 忽略"今日已推送"去重
```

也可以直接双击 `run.bat`（默认走 digest）。

## 定时任务

| 任务名 | 频率 | 说明 |
|---|---|---|
| `SunsetGlow_Digest` | 每 6 小时（06:12 / 12:12 / 18:12 / 00:12） | 常规检查，只在今天达到高分线时推送 |
| `SunsetGlow_PreSunset` | 每天 14:00–20:00 每小时 | 日落前窗口检查，达标时加推一条提醒你出门；每天最多一条 |

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
