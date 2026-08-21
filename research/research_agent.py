"""
リサーチAgent: 楽天ウェブサービス(RWS) 商品検索APIで、その日のジャンルのトレンド候補商品を集める。

投稿の実行は行わない（規約により人間が行う）。ここでは商品候補データを集めて
research/配下にJSONで保存し、人間・後続のライティングAgentが参照できるようにするだけ。

使い方:
    python research_agent.py                # 今日の曜日に対応するジャンルで実行
    python research_agent.py --genre gadget  # ジャンルを指定して実行
    python research_agent.py --hits 15       # 1キーワードあたりの取得件数を変更
"""

import argparse
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

# Windowsのコンソール(cp932)でも日本語・記号を文字化けさせずに出力するため
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

APP_ID = os.getenv("RAKUTEN_APP_ID")
AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID")
ACCESS_KEY = os.getenv("RAKUTEN_ACCESS_KEY")
# Rakuten Developersの「Application URL」に登録したURL。Referer/Originのドメイン一致チェックに必要
REFERER = os.getenv("RAKUTEN_REFERER", "https://room.rakuten.co.jp/room_6e370bb0f4/items")
REQUEST_INTERVAL_SEC = 1.2  # Expected QPS=1で登録しているため、リクエスト間隔を空ける

# 2026年2月の楽天API基盤刷新により、旧エンドポイント(app.rakuten.co.jp/services/api)は
# 2026-05-14で廃止。新エンドポイント(openapi.rakuten.co.jp/ichibams/api)ではapplicationIdに
# 加えてaccessKey(pk_から始まる)が必須。 https://webservice.rakuten.co.jp/documentation/ichiba-item-search
SEARCH_ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"

# docs/02_genre_test_plan.md のローテーションに対応
WEEKDAY_GENRE = {
    0: "gadget",    # 月
    1: "beauty",    # 火
    2: "kitchen",   # 水
    3: "gadget",    # 木
    4: "beauty",    # 金
    5: "kitchen",   # 土
    6: "summary",   # 日（週次まとめ枠。ここでは前日ジャンルを再利用）
}

GENRE_KEYWORDS = {
    "gadget": ["ガジェット 新商品", "モバイルバッテリー 人気", "スマート家電"],
    "beauty": ["コスメ 新作", "スキンケア 人気", "美容 話題"],
    "kitchen": ["キッチン 便利グッズ", "収納 アイデア", "お弁当グッズ"],
}

# 楽天市場ジャンルID（IchibaGenre/Search, genreId=0のルート一覧から取得）
# キーワード検索だけだとジャンルと無関係な商品が混入する(例: 美容ジャンルでミックスナッツがヒット)ため、
# genreIdで必ず絞り込む。
GENRE_IDS = {
    "gadget": 562637,   # 家電
    "beauty": 100939,   # 美容・コスメ・香水
    "kitchen": 558944,  # キッチン用品・食器・調理器具
}


def fetch_items(keyword: str, genre_id: int, hits: int = 10) -> list[dict]:
    if not APP_ID:
        raise RuntimeError("RAKUTEN_APP_ID が .env に設定されていません")
    if not ACCESS_KEY:
        raise RuntimeError(
            "RAKUTEN_ACCESS_KEY が .env に設定されていません。"
            "webservice.rakuten.co.jp/app/list で対象アプリのAccess Key(pk_...)を確認してください。"
        )

    params = {
        "format": "json",
        "keyword": keyword,
        "genreId": genre_id,
        "applicationId": APP_ID,
        "accessKey": ACCESS_KEY,
        "hits": hits,
        "sort": "-reviewCount",
    }
    if AFFILIATE_ID:
        params["affiliateId"] = AFFILIATE_ID

    headers = {
        "Referer": REFERER,
        "Origin": "https://" + REFERER.split("/")[2],
    }
    res = requests.get(SEARCH_ENDPOINT, params=params, headers=headers, timeout=10)
    res.raise_for_status()
    data = res.json()

    items = []
    for entry in data.get("Items", []):
        item = entry.get("Item", entry)
        items.append(
            {
                "itemName": item.get("itemName"),
                "itemPrice": item.get("itemPrice"),
                "itemUrl": item.get("itemUrl"),
                "affiliateUrl": item.get("affiliateUrl") or item.get("itemUrl"),
                "shopName": item.get("shopName"),
                "reviewCount": item.get("reviewCount"),
                "reviewAverage": item.get("reviewAverage"),
                "imageUrl": (item.get("mediumImageUrls") or [{}])[0].get("imageUrl"),
                "itemCode": item.get("itemCode"),
                "searchKeyword": keyword,
            }
        )
    return items


def run_research(genre: str, hits_per_keyword: int = 10, top_n: int = 15) -> dict:
    keywords = GENRE_KEYWORDS.get(genre)
    genre_id = GENRE_IDS.get(genre)
    if not keywords or not genre_id:
        raise ValueError(f"未知のジャンルです: {genre}. 選択肢: {list(GENRE_KEYWORDS)}")

    seen = {}
    for i, kw in enumerate(keywords):
        if i > 0:
            time.sleep(REQUEST_INTERVAL_SEC)
        try:
            for item in fetch_items(kw, genre_id, hits=hits_per_keyword):
                code = item.get("itemCode")
                if code and code not in seen:
                    seen[code] = item
        except requests.HTTPError as e:
            print(f"[警告] キーワード '{kw}' の取得に失敗しました: {e}", file=sys.stderr)

    ranked = sorted(
        seen.values(),
        key=lambda x: (x.get("reviewCount") or 0),
        reverse=True,
    )[:top_n]

    return {
        "genre": genre,
        "keywords": keywords,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "item_count": len(ranked),
        "items": ranked,
    }


def main():
    parser = argparse.ArgumentParser(description="楽天ROOM リサーチAgent")
    parser.add_argument("--genre", choices=list(GENRE_KEYWORDS), help="ジャンルを指定（省略時は曜日から自動判定）")
    parser.add_argument("--hits", type=int, default=10, help="1キーワードあたりの取得件数")
    parser.add_argument("--top", type=int, default=15, help="保存する上位件数")
    args = parser.parse_args()

    genre = args.genre or WEEKDAY_GENRE.get(date.today().weekday(), "gadget")
    if genre == "summary":
        genre = WEEKDAY_GENRE.get((date.today().weekday() - 1) % 7, "gadget")

    print(f"ジャンル '{genre}' でリサーチを実行します...")
    result = run_research(genre, hits_per_keyword=args.hits, top_n=args.top)

    out_dir = PROJECT_ROOT / "research"
    out_path = out_dir / f"{date.today().isoformat()}_{genre}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{result['item_count']}件を保存しました -> {out_path}")
    print("\n--- 上位候補 ---")
    for i, item in enumerate(result["items"][:5], start=1):
        print(f"{i}. {item['itemName']} / ¥{item['itemPrice']} / レビュー{item['reviewCount']}件({item['reviewAverage']})")
        print(f"   {item['affiliateUrl']}")


if __name__ == "__main__":
    main()
