# Linux / systemd 部署

运行依赖：Python 3.9+、git、flock、systemd。无 pip 依赖，无端口，无常驻 Python 进程。

安装到 /opt/sunset-glow，创建专用系统用户 sunset-glow。将 service 和 timer 模板安装到 /etc/systemd/system，logrotate 模板安装到 /etc/logrotate.d/sunset-glow，daemon-reload 后启用两个 timer。

状态：/var/lib/sunset-glow/state.json。日志：/var/log/sunset-glow。目录由 sunset-glow 持有、权限 700；迁移已有 state.json 时设置 sunset-glow 所有者、权限 600。

凭据：/etc/sunset-glow.env，填写 PUSHPLUS_TOKEN 环境变量，root 持有、权限 600，不进仓库。缺文件时 systemd 跳过任务。代码更新不会覆盖状态、日志或凭据。

常规检查：北京时间 00:12 / 06:12 / 12:12 / 18:12。临场检查：14:07–20:07 每小时。timer 直接指定 Asia/Shanghai，不补跑错过的旧任务。

关闭 GitHub Actions 的两个定时 workflow，避免独立去重状态造成重复推送。Actions 保留备用。

单次上限：300 秒、96 MB 内存、20% CPU，flock 避免并发写状态。

验证：python3 -m unittest discover -s tests -v。
查看任务：systemctl list-timers 'sunset-glow-*' --all。
查看日志：journalctl -u 'sunset-glow@*' -n 80 --no-pager。
有 token 后测试：systemctl start sunset-glow@test.service。

发送失败返回退出码 1，不写去重，后续同类型检查在有效窗口内可重试。API 成功表示第三方接收，不能证明微信端送达；若第三方接收后响应丢失，可能重复。

更新前备份状态并记录 commit，git pull --ff-only 后跑回归测试。回滚先停 timer、切回原 commit；更改模板后重新安装并 daemon-reload。
