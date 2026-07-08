# SteamLens

[在线体验](https://3takagi.github.io/steamlens/) · 本地运行无需外部 AI API

Steam 游戏口碑与版本洞察平台。首版包含四款游戏各 500 条最新公开评论：

- Monster Hunter Wilds
- HELLDIVERS 2
- Cities: Skylines II
- Cyberpunk 2077

## 项目亮点

- Steam 公开评论增量采集、评论 ID 去重与每日快照。
- 多语言主题分析、玩家时长分层、置信区间与小样本提示。
- 字符级 TF-IDF + 逻辑回归情感分类，包含随机留出和跨游戏泛化评估。
- 数据质量门槛、混淆矩阵、高置信度错例与原始证据追溯。
- 当前模型 Accuracy 82.3%，Macro F1 0.758。

公开仓库仅包含匿名、截断后的展示数据。完整本地评论库、日志、虚拟环境和模型二进制不会上传。

## 使用

双击 `start.bat`，浏览器会打开 `http://127.0.0.1:8096/`。

## 更新数据

双击 `refresh-data.bat`，或运行：

```powershell
E:\codex\tools\Python310\python.exe scripts\collect.py
```

采集脚本只使用 Python 标准库，不需要 Steam API Key。页面数据来自 `data/steam-reviews.json`，浏览分析时不需要联网。

## 定期更新

在线版由 GitHub Actions 在北京时间每天 09:15 自动采集、分析并重新部署，不依赖个人电脑开机。也可以在仓库的 **Actions > Refresh Steam data > Run workflow** 中立即触发更新。

- `enable-daily-refresh.bat`：启用每天 09:00 自动更新。
- `refresh-status.bat`：查看任务状态、下次运行时间和上次结果。
- `disable-auto-refresh.bat`：取消自动更新。

自动更新使用 Windows 任务计划程序。错过执行时间时会在下次登录后补跑；日志保存在 `logs/refresh-YYYY-MM-DD.log`，并自动清理 30 天以前的日志。

也可以自定义周期：

```powershell
# 每天 18:30
powershell -ExecutionPolicy Bypass -File schedule-refresh.ps1 -Frequency Daily -Time 18:30

# 每周一 09:00
powershell -ExecutionPolicy Bypass -File schedule-refresh.ps1 -Frequency Weekly -DayOfWeek Monday -Time 09:00
```

## 当前分析范围

当前样本采用每款游戏最新 500 条公开评论，包含多语言和 Steam 标记的非主题活动。它适合观察近期口碑，不应被解释为完整历史趋势。主题分类使用可核验的多语言关键词规则，所有结论均可回到原始评论检查。

数据刷新不会再丢弃历史：

- `data/steam-reviews.json`：网页使用的当前 500 条样本与每日快照。
- `data/review-store.json`：按评论 ID 去重的累计评论库，并保留最近的修改记录。
- `data/snapshots.json`：最多保留 180 个采集日的推荐率和主题指标。

页面中的推荐率、语言差异和玩家分层会显示 95% 置信区间；少于 30 条的分组会标记为小样本，不直接用于强结论。

## 本地 AI 分析

首次双击 `run-analysis.bat` 会在项目内创建独立 `.venv`，安装 `scikit-learn`，随后生成：

- `data/model-analysis.json`：网页使用的数据质量和模型评估结果。
- `models/sentiment-tfidf-logreg.joblib`：训练后的本地情感分类模型。
- `reports/data-quality-report.md`：数据质量报告。
- `reports/model-card.md`：模型方法、指标和限制。

模型采用多语言字符级 TF-IDF 与逻辑回归，不调用外部 AI API。定时更新在分析环境存在时会自动重新训练模型并刷新评估结果。
