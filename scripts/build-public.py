from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "public-data"


def review_for_public(review: dict) -> dict:
    return {
        "id": review.get("id", ""),
        "language": review.get("language", "unknown"),
        "review": (review.get("review") or "")[:360],
        "created": review.get("created", 0),
        "voted_up": bool(review.get("voted_up")),
        "votes_up": int(review.get("votes_up") or 0),
        "playtime_at_review": int(review.get("playtime_at_review") or 0),
        "topics": review.get("topics") or [],
    }


def main() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    reviews = json.loads((DATA_DIR / "steam-reviews.json").read_text(encoding="utf-8"))
    analysis = json.loads((DATA_DIR / "model-analysis.json").read_text(encoding="utf-8"))

    public_reviews = {
        key: reviews[key]
        for key in ("generated_at", "source", "sample_strategy", "topic_rules", "snapshots")
        if key in reviews
    }
    public_reviews["publication_note"] = "Anonymous public-review excerpts; text is truncated for portfolio display."
    public_reviews["games"] = []
    for game in reviews["games"]:
        public_game = {
            key: game[key]
            for key in ("app_id", "slug", "name", "name_zh", "accent", "released", "focus", "image", "query_summary", "history_store")
            if key in game
        }
        public_game["reviews"] = [review_for_public(review) for review in game["reviews"]]
        public_reviews["games"].append(public_game)

    public_analysis = json.loads(json.dumps(analysis, ensure_ascii=False))
    for error in public_analysis.get("model", {}).get("errors", []):
        error.pop("id", None)
        error["text"] = (error.get("text") or "")[:360]

    (PUBLIC_DIR / "steam-reviews.json").write_text(
        json.dumps(public_reviews, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (PUBLIC_DIR / "model-analysis.json").write_text(
        json.dumps(public_analysis, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"Public reviews: {(PUBLIC_DIR / 'steam-reviews.json').stat().st_size / 1024:.1f} KB")
    print(f"Public analysis: {(PUBLIC_DIR / 'model-analysis.json').stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
