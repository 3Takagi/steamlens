from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ASSET_DIR = ROOT / "assets"
TARGET_COUNT = 500
STORE_PATH = DATA_DIR / "review-store.json"
SNAPSHOT_PATH = DATA_DIR / "snapshots.json"
PUBLIC_DATA_PATH = ROOT / "public-data" / "steam-reviews.json"

TOPIC_RULES = [
    {"id": "performance", "name": "性能与优化", "description": "帧率、卡顿、显存、CPU/GPU 占用与硬件适配问题。", "words": ["performance", "fps", "frame rate", "stutter", "lag", "optimization", "optimiz", "crash", "性能", "优化", "帧", "卡顿", "闪退", "崩溃", "显存", "cpu", "gpu", "フレーム", "最適化", "クラッシュ", "성능", "프레임"]},
    {"id": "bugs", "name": "Bug 与稳定性", "description": "影响正常游玩的错误、存档、连接失败和功能异常。", "words": ["bug", "broken", "error", "freeze", "glitch", "issue", "disconnect", "server", "matchmaking", "错误", "故障", "存档", "断线", "服务器", "联机", "バグ", "不具合", "サーバー", "버그", "서버"]},
    {"id": "content", "name": "内容与重复度", "description": "内容量、后期体验、任务重复与更新内容是否充足。", "words": ["content", "endgame", "repetitive", "boring", "mission", "quest", "update", "内容", "重复", "无聊", "任务", "后期", "更新", "コンテンツ", "飽き", "クエスト", "콘텐츠", "반복"]},
    {"id": "balance", "name": "玩法与平衡", "description": "战斗、难度、数值、武器与核心循环体验。", "words": ["balance", "difficulty", "combat", "weapon", "enemy", "gameplay", "nerf", "buff", "平衡", "难度", "战斗", "武器", "数值", "削弱", "加强", "バランス", "武器", "戦闘", "밸런스", "전투"]},
    {"id": "price", "name": "价格与商业化", "description": "售价、DLC、微交易、性价比和商业策略争议。", "words": ["price", "expensive", "dlc", "microtransaction", "money", "refund", "worth", "价格", "售价", "退款", "氪金", "微交易", "性价比", "値段", "課金", "환불", "가격"]},
    {"id": "ux", "name": "界面与易用性", "description": "操作、菜单、引导、控制器和整体使用体验。", "words": ["ui", "ux", "menu", "control", "tutorial", "interface", "keyboard", "controller", "操作", "界面", "菜单", "引导", "手柄", "键鼠", "操作性", "メニュー", "操作", "조작", "인터페이스"]},
    {"id": "community", "name": "账号与社区事件", "description": "账号绑定、地区限制、反作弊和开发商沟通。", "words": ["account", "psn", "region", "sony", "developer", "community", "anti-cheat", "ban", "账号", "绑定", "地区", "索尼", "运营", "社区", "封禁", "アカウント", "地域", "계정", "지역"]},
]

GAMES = [
    {
        "app_id": 2246340,
        "slug": "monster-hunter-wilds",
        "name": "Monster Hunter Wilds",
        "name_zh": "怪物猎人：荒野",
        "accent": "#53e3c2",
        "released": "2025-02-28",
        "focus": "性能优化、稳定性与更新后的口碑恢复",
    },
    {
        "app_id": 553850,
        "slug": "helldivers-2",
        "name": "HELLDIVERS 2",
        "name_zh": "绝地潜兵 2",
        "accent": "#f4c84b",
        "released": "2024-02-08",
        "focus": "账号争议、社区事件与联机体验",
    },
    {
        "app_id": 949230,
        "slug": "cities-skylines-2",
        "name": "Cities: Skylines II",
        "name_zh": "都市：天际线 II",
        "accent": "#6db6ff",
        "released": "2023-10-24",
        "focus": "性能、内容完整度与长期修复",
    },
    {
        "app_id": 1091500,
        "slug": "cyberpunk-2077",
        "name": "Cyberpunk 2077",
        "name_zh": "赛博朋克 2077",
        "accent": "#ff596f",
        "released": "2020-12-10",
        "focus": "长期版本迭代与口碑逆转",
    },
]


def request_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SteamLens/0.1 (+local portfolio analysis)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_snapshots() -> dict:
    """Keep trend history when a cloud runner starts from a clean checkout."""
    local = load_json(SNAPSHOT_PATH, {})
    if local.get("snapshots"):
        return local
    public = load_json(PUBLIC_DATA_PATH, {})
    return {"schema": 1, "snapshots": public.get("snapshots") or []}


def classify_review(text: str) -> list[str]:
    normalized = text.lower()
    return [rule["id"] for rule in TOPIC_RULES if any(word.lower() in normalized for word in rule["words"])]


def snapshot_metrics(reviews: list[dict]) -> dict:
    topic_metrics = {}
    for rule in TOPIC_RULES:
        matched = [review for review in reviews if rule["id"] in review["topics"]]
        negatives = [review for review in matched if not review["voted_up"]]
        topic_metrics[rule["id"]] = {
            "mentions": len(matched),
            "negatives": len(negatives),
            "negative_rate": round(len(negatives) / len(matched), 4) if matched else 0,
        }
    return {
        "sample_count": len(reviews),
        "positive_rate": round(sum(review["voted_up"] for review in reviews) / len(reviews), 4) if reviews else 0,
        "topics": topic_metrics,
    }


def merge_review_store(store: dict, app_id: int, reviews: list[dict], seen_at: str) -> dict:
    game_store = store.setdefault("games", {}).setdefault(str(app_id), {"reviews": {}})
    stored_reviews = game_store.setdefault("reviews", {})
    added = 0
    edited = 0
    for review in reviews:
        review_id = review["id"]
        previous = stored_reviews.get(review_id)
        if previous is None:
            stored_reviews[review_id] = {**review, "first_seen": seen_at, "last_seen": seen_at, "edit_count": 0, "revisions": []}
            added += 1
            continue
        changed = previous.get("review") != review["review"] or previous.get("voted_up") != review["voted_up"]
        revisions = previous.get("revisions", [])
        edit_count = int(previous.get("edit_count") or 0)
        if changed:
            revisions = [
                *revisions[-4:],
                {"seen_at": seen_at, "review": previous.get("review", ""), "voted_up": previous.get("voted_up"), "updated": previous.get("updated", 0)},
            ]
            edit_count += 1
            edited += 1
        stored_reviews[review_id] = {
            **previous,
            **review,
            "first_seen": previous.get("first_seen", seen_at),
            "last_seen": seen_at,
            "edit_count": edit_count,
            "revisions": revisions,
        }
    game_store["unique_reviews"] = len(stored_reviews)
    return {"added": added, "edited": edited, "total": len(stored_reviews)}


def collect_reviews(app_id: int, target: int) -> tuple[list[dict], dict]:
    cursor = "*"
    reviews: list[dict] = []
    seen: set[str] = set()
    summary: dict = {}

    while len(reviews) < target:
        params = urllib.parse.urlencode(
            {
                "json": 1,
                "filter": "recent",
                "language": "all",
                "purchase_type": "all",
                "num_per_page": 100,
                "cursor": cursor,
                "filter_offtopic_activity": 0,
            }
        )
        payload = request_json(f"https://store.steampowered.com/appreviews/{app_id}?{params}")
        if payload.get("success") != 1:
            raise RuntimeError(f"Steam returned an unsuccessful response for {app_id}")
        if not summary:
            summary = payload.get("query_summary") or {}

        batch = payload.get("reviews") or []
        if not batch:
            break
        for item in batch:
            recommendation_id = str(item.get("recommendationid") or "")
            if not recommendation_id or recommendation_id in seen:
                continue
            seen.add(recommendation_id)
            author = item.get("author") or {}
            reviews.append(
                {
                    "id": recommendation_id,
                    "language": item.get("language") or "unknown",
                    "review": item.get("review") or "",
                    "created": int(item.get("timestamp_created") or 0),
                    "updated": int(item.get("timestamp_updated") or 0),
                    "voted_up": bool(item.get("voted_up")),
                    "votes_up": int(item.get("votes_up") or 0),
                    "votes_funny": int(item.get("votes_funny") or 0),
                    "weighted_vote_score": float(item.get("weighted_vote_score") or 0),
                    "steam_purchase": bool(item.get("steam_purchase")),
                    "received_for_free": bool(item.get("received_for_free")),
                    "early_access": bool(item.get("written_during_early_access")),
                    "playtime_forever": int(author.get("playtime_forever") or 0),
                    "playtime_at_review": int(author.get("playtime_at_review") or 0),
                    "games_owned": int(author.get("num_games_owned") or 0),
                    "reviews_written": int(author.get("num_reviews") or 0),
                    "topics": classify_review(item.get("review") or ""),
                }
            )
            if len(reviews) >= target:
                break

        cursor = payload.get("cursor") or ""
        if not cursor:
            break
        print(f"  {app_id}: {len(reviews)}/{target}")
        time.sleep(0.45)

    return reviews, summary


def download_header(game: dict) -> str:
    filename = f"{game['slug']}.jpg"
    destination = ASSET_DIR / filename
    url = f"https://cdn.akamai.steamstatic.com/steam/apps/{game['app_id']}/header.jpg"
    request = urllib.request.Request(url, headers={"User-Agent": "SteamLens/0.1"})
    with urllib.request.urlopen(request, timeout=25) as response:
        destination.write_bytes(response.read())
    return f"assets/{filename}"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    snapshot_date = datetime.now().astimezone().date().isoformat()
    store = load_json(STORE_PATH, {"schema": 1, "games": {}})
    snapshots = load_snapshots()
    result = {
        "generated_at": generated_at,
        "source": "Steam public user reviews endpoint",
        "sample_strategy": "Latest 500 public reviews per game, all languages, off-topic activity included",
        "topic_rules": [{key: value for key, value in rule.items() if key != "words"} for rule in TOPIC_RULES],
        "games": [],
    }
    daily_snapshot = {"date": snapshot_date, "generated_at": generated_at, "games": {}}

    for game in GAMES:
        print(f"Collecting {game['name']}...")
        reviews, summary = collect_reviews(game["app_id"], TARGET_COUNT)
        entry = dict(game)
        entry["image"] = download_header(game)
        entry["query_summary"] = summary
        entry["reviews"] = reviews
        store_result = merge_review_store(store, game["app_id"], reviews, generated_at)
        entry["history_store"] = store_result
        daily_snapshot["games"][str(game["app_id"])] = snapshot_metrics(reviews)
        result["games"].append(entry)
        print(f"  saved {len(reviews)} reviews; {store_result['added']} new, {store_result['edited']} edited, {store_result['total']} unique")

    existing_snapshots = [item for item in snapshots.get("snapshots", []) if item.get("date") != snapshot_date]
    snapshots["snapshots"] = [*existing_snapshots[-179:], daily_snapshot]
    result["snapshots"] = snapshots["snapshots"]

    output = DATA_DIR / "steam-reviews.json"
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    STORE_PATH.write_text(json.dumps(store, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    SNAPSHOT_PATH.write_text(json.dumps(snapshots, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {output} ({output.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
