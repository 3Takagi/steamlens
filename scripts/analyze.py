from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "steam-reviews.json"
OUTPUT_PATH = ROOT / "data" / "model-analysis.json"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
RANDOM_STATE = 42


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def make_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 5),
                    min_df=2,
                    max_features=35000,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1200,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


def classification_metrics(actual: list[int], predicted: list[int]) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(
        actual, predicted, average="binary", zero_division=0
    )
    _, _, macro_f1, _ = precision_recall_fscore_support(
        actual, predicted, average="macro", zero_division=0
    )
    matrix = confusion_matrix(actual, predicted, labels=[0, 1]).tolist()
    return {
        "accuracy": round(float(accuracy_score(actual, predicted)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "macro_f1": round(float(macro_f1), 4),
        "confusion_matrix": matrix,
    }


def quality_report(data: dict, rows: list[dict], model_rows: list[dict]) -> dict:
    normalized = [normalize_text(row["text"]) for row in rows]
    hashes = [hashlib.sha256(text.encode("utf-8")).hexdigest() for text in normalized if text]
    hash_counts = Counter(hashes)
    duplicate_rows = sum(count - 1 for count in hash_counts.values() if count > 1)
    short_rows = sum(len(re.sub(r"\s+", "", row["text"])) < 10 for row in rows)
    missing_rows = sum(not row["text"].strip() for row in rows)
    topic_rows = sum(bool(row["topics"]) for row in rows)
    languages = Counter(row["language"] for row in rows)
    games = []
    for game in data["games"]:
        game_rows = [row for row in rows if row["app_id"] == game["app_id"]]
        games.append(
            {
                "app_id": game["app_id"],
                "name": game["name_zh"],
                "rows": len(game_rows),
                "positive_rate": round(sum(row["label"] for row in game_rows) / len(game_rows), 4),
                "topic_coverage": round(sum(bool(row["topics"]) for row in game_rows) / len(game_rows), 4),
                "short_rate": round(sum(len(re.sub(r"\s+", "", row["text"])) < 10 for row in game_rows) / len(game_rows), 4),
            }
        )
    return {
        "total_rows": len(rows),
        "analysis_ready_rows": len(model_rows),
        "removed_rows": len(rows) - len(model_rows),
        "missing_text": missing_rows,
        "short_text": short_rows,
        "short_rate": round(short_rows / len(rows), 4),
        "exact_duplicate_rows": duplicate_rows,
        "duplicate_rate": round(duplicate_rows / len(rows), 4),
        "topic_coverage": round(topic_rows / len(rows), 4),
        "language_count": len(languages),
        "top_languages": [{"language": name, "count": count} for name, count in languages.most_common(10)],
        "games": games,
        "checks": [
            {"name": "有效文本进入模型", "passed": all(row["text"].strip() for row in model_rows), "detail": f"移除空文本 {missing_rows} 条"},
            {"name": "训练数据完成去重", "passed": len({normalize_text(row['text']) for row in model_rows}) == len(model_rows), "detail": f"移除重复及无效记录 {len(rows) - len(model_rows)} 条"},
            {"name": "主题覆盖可用", "passed": topic_rows / len(rows) >= 0.5, "detail": f"覆盖率 {topic_rows / len(rows):.1%}"},
            {"name": "多语言样本", "passed": len(languages) >= 4, "detail": f"覆盖 {len(languages)} 种语言"},
        ],
    }


def build_rows(data: dict) -> list[dict]:
    rows = []
    for game in data["games"]:
        for review in game["reviews"]:
            rows.append(
                {
                    "id": review["id"],
                    "app_id": game["app_id"],
                    "game": game["name_zh"],
                    "language": review["language"],
                    "text": review["review"],
                    "label": int(review["voted_up"]),
                    "topics": review.get("topics") or [],
                }
            )
    return rows


def deduplicate_for_model(rows: list[dict]) -> list[dict]:
    unique = {}
    for row in rows:
        normalized = normalize_text(row["text"])
        if normalized:
            unique.setdefault(normalized, row)
    return list(unique.values())


def random_holdout(rows: list[dict]) -> tuple[dict, Pipeline, list[dict]]:
    indices = np.arange(len(rows))
    labels = np.array([row["label"] for row in rows])
    train_indices, test_indices = train_test_split(
        indices,
        test_size=0.22,
        random_state=RANDOM_STATE,
        stratify=labels,
    )
    train_texts = [rows[index]["text"] for index in train_indices]
    train_labels = [rows[index]["label"] for index in train_indices]
    test_texts = [rows[index]["text"] for index in test_indices]
    test_labels = [rows[index]["label"] for index in test_indices]

    pipeline = make_pipeline()
    pipeline.fit(train_texts, train_labels)
    predicted = pipeline.predict(test_texts)
    probabilities = pipeline.predict_proba(test_texts)
    metrics = classification_metrics(test_labels, predicted.tolist())
    majority = int(sum(train_labels) >= len(train_labels) / 2)
    baseline = [majority] * len(test_labels)
    metrics["majority_baseline_accuracy"] = round(float(accuracy_score(test_labels, baseline)), 4)
    metrics["train_rows"] = len(train_indices)
    metrics["test_rows"] = len(test_indices)

    errors = []
    for local_index, row_index in enumerate(test_indices):
        if int(predicted[local_index]) == int(test_labels[local_index]):
            continue
        confidence = float(max(probabilities[local_index]))
        row = rows[int(row_index)]
        errors.append(
            {
                "id": row["id"],
                "game": row["game"],
                "language": row["language"],
                "text": row["text"][:600],
                "actual": int(test_labels[local_index]),
                "predicted": int(predicted[local_index]),
                "confidence": round(confidence, 4),
            }
        )
    errors.sort(key=lambda item: item["confidence"], reverse=True)
    return metrics, pipeline, errors[:24]


def cross_game_validation(rows: list[dict]) -> list[dict]:
    results = []
    app_ids = sorted(set(row["app_id"] for row in rows))
    for app_id in app_ids:
        train = [row for row in rows if row["app_id"] != app_id]
        test = [row for row in rows if row["app_id"] == app_id]
        pipeline = make_pipeline()
        pipeline.fit([row["text"] for row in train], [row["label"] for row in train])
        predicted = pipeline.predict([row["text"] for row in test]).tolist()
        metrics = classification_metrics([row["label"] for row in test], predicted)
        results.append(
            {
                "app_id": app_id,
                "game": test[0]["game"],
                "train_rows": len(train),
                "test_rows": len(test),
                **metrics,
            }
        )
    return results


def feature_examples(pipeline: Pipeline) -> dict:
    vectorizer = pipeline.named_steps["tfidf"]
    classifier = pipeline.named_steps["classifier"]
    names = np.array(vectorizer.get_feature_names_out())
    coefficients = classifier.coef_[0]
    return {
        "positive": names[np.argsort(coefficients)[-18:][::-1]].tolist(),
        "negative": names[np.argsort(coefficients)[:18]].tolist(),
    }


def write_reports(result: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    quality = result["quality"]
    model = result["model"]
    quality_lines = [
        "# SteamLens 数据质量报告",
        "",
        f"生成时间：{result['generated_at']}",
        "",
        f"- 总评论数：{quality['total_rows']}",
        f"- 分析可用评论：{quality['analysis_ready_rows']}（清洗移除 {quality['removed_rows']} 条）",
        f"- 缺失正文：{quality['missing_text']}",
        f"- 精确重复：{quality['exact_duplicate_rows']}（{quality['duplicate_rate']:.1%}）",
        f"- 极短评论：{quality['short_text']}（{quality['short_rate']:.1%}）",
        f"- 主题覆盖率：{quality['topic_coverage']:.1%}",
        f"- 语言数量：{quality['language_count']}",
    ]
    (REPORT_DIR / "data-quality-report.md").write_text("\n".join(quality_lines), encoding="utf-8")

    model_lines = [
        "# SteamLens 情感分类模型卡",
        "",
        "## 任务",
        "",
        "根据公开评论正文预测 Steam 推荐/不推荐标签。",
        "",
        "## 方法",
        "",
        "字符级 TF-IDF（2-5 gram）+ class-weighted Logistic Regression。模型完全在本地训练，不调用外部 AI API。",
        "",
        "## 随机留出集结果",
        "",
        f"- Accuracy：{model['holdout']['accuracy']:.3f}",
        f"- Macro F1：{model['holdout']['macro_f1']:.3f}",
        f"- Positive F1：{model['holdout']['f1']:.3f}",
        f"- Majority baseline：{model['holdout']['majority_baseline_accuracy']:.3f}",
        "",
        "## 限制",
        "",
        "Steam 推荐标签不等同于纯文本情绪；反讽、短文本、混合语言和游戏专有表达仍可能造成误判。",
    ]
    (REPORT_DIR / "model-card.md").write_text("\n".join(model_lines), encoding="utf-8")


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    rows = build_rows(data)
    model_rows = deduplicate_for_model(rows)
    quality = quality_report(data, rows, model_rows)
    holdout, pipeline, errors = random_holdout(model_rows)
    cross_game = cross_game_validation(model_rows)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_DIR / "sentiment-tfidf-logreg.joblib", compress=3)

    result = {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_generated_at": data["generated_at"],
        "quality": quality,
        "model": {
            "name": "Character TF-IDF + Logistic Regression",
            "task": "Predict Steam recommended / not recommended labels from multilingual review text",
            "model_rows": len(model_rows),
            "holdout": holdout,
            "cross_game": cross_game,
            "feature_examples": feature_examples(pipeline),
            "errors": errors,
        },
    }
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    write_reports(result)
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Holdout accuracy: {holdout['accuracy']:.3f}; macro F1: {holdout['macro_f1']:.3f}")
    for item in cross_game:
        print(f"Cross-game {item['game']}: accuracy={item['accuracy']:.3f}, macro_f1={item['macro_f1']:.3f}")


if __name__ == "__main__":
    main()
