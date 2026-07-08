# SteamLens 情感分类模型卡

## 任务

根据公开评论正文预测 Steam 推荐/不推荐标签。

## 方法

字符级 TF-IDF（2-5 gram）+ class-weighted Logistic Regression。模型完全在本地训练，不调用外部 AI API。

## 随机留出集结果

- Accuracy：0.823
- Macro F1：0.758
- Positive F1：0.883
- Majority baseline：0.757

## 限制

Steam 推荐标签不等同于纯文本情绪；反讽、短文本、混合语言和游戏专有表达仍可能造成误判。