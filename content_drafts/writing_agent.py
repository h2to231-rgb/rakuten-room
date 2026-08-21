"""
ライティングAgent（テンプレートベース、API不要）

リサーチAgent(research/research_agent.py)が保存したJSONを読み込み、
docs/04_pr_disclosure_guidelines.md のルールに沿った投稿下書きをテンプレートで生成する。
断定的な効果表現やNo.1表現は使わず、価格・レビュー件数など事実ベースの情報のみで構成する。

生成した下書きは自動でcompliance/pr_checker.pyのチェックにかけ、結果を一緒に表示する。
投稿の実行は行わない（人間が内容を確認し、ROOMで手動投稿する）。

使い方:
    python content_drafts/writing_agent.py                # 今日の日付・自動判定ジャンルの最新リサーチ結果を使用
    python content_drafts/writing_agent.py --genre beauty  # ジャンルを指定
    python content_drafts/writing_agent.py --top 3          # 上位何件のドラフトを作るか
"""

import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "compliance"))
sys.stdout.reconfigure(encoding="utf-8")

from pr_checker import check_text, format_report  # noqa: E402

PR_DISCLOSURE = "【PR】本投稿には楽天アフィリエイトリンクを含みます。商品購入により紹介料を得ることがあります。"

INTRO_TEMPLATES = {
    "gadget": [
        "最近リサーチしていて気になったガジェットです。",
        "毎日の暮らしを少し便利にしてくれそうな一品を見つけました。",
    ],
    "beauty": [
        "気になっていたコスメを見つけたのでシェアします。",
        "最近リサーチ中に目に留まった一品です。",
    ],
    "kitchen": [
        "キッチンがちょっと快適になりそうなアイテムを見つけました。",
        "日々の家事が楽になりそうなグッズです。",
    ],
}

CLOSING_TEMPLATES = [
    "参考になれば嬉しいです。",
    "気になった方はぜひ商品ページをチェックしてみてください。",
]

HASHTAGS = {
    "gadget": "#ガジェット #楽天ROOM #楽天市場",
    "beauty": "#コスメ #楽天ROOM #楽天市場",
    "kitchen": "#キッチングッズ #楽天ROOM #楽天市場",
}


def build_draft(item: dict, genre: str, fetched_at: str) -> str:
    rnd = random.Random(item.get("itemCode"))  # itemCodeでseedし、再実行しても同じ文面になるようにする
    intro = rnd.choice(INTRO_TEMPLATES.get(genre, INTRO_TEMPLATES["gadget"]))
    closing = rnd.choice(CLOSING_TEMPLATES)

    review_count = item.get("reviewCount") or 0
    review_avg = item.get("reviewAverage")
    if review_count and review_avg:
        review_sentence = f"レビュー{review_count}件・評価{review_avg}と、多くの方に購入されている商品のようです（{fetched_at}時点の情報です）。"
    else:
        review_sentence = f"（{fetched_at}時点の情報です。レビュー件数はまだ多くありません）"

    lines = [
        PR_DISCLOSURE,
        "",
        intro,
        "",
        f"▼商品名\n{item.get('itemName')}",
        "",
        f"▼価格\n¥{item.get('itemPrice')}（{fetched_at}時点、実際の価格は商品ページでご確認ください）",
        "",
        "▼おすすめポイント",
        review_sentence,
        "気になる方は商品ページで詳細をチェックしてみてください。",
        "",
        closing,
        "",
        item.get("affiliateUrl") or item.get("itemUrl"),
        "",
        HASHTAGS.get(genre, HASHTAGS["gadget"]),
    ]
    return "\n".join(lines)


def find_latest_research_file(genre: str) -> Path | None:
    candidates = sorted((PROJECT_ROOT / "research").glob(f"*_{genre}.json"), reverse=True)
    return candidates[0] if candidates else None


def main():
    parser = argparse.ArgumentParser(description="楽天ROOM ライティングAgent（テンプレートベース）")
    parser.add_argument("--genre", help="対象ジャンル（gadget/beauty/kitchen）。省略時は最新の研究データを自動探索")
    parser.add_argument("--top", type=int, default=3, help="ドラフトを作る商品数（上位N件）")
    args = parser.parse_args()

    if args.genre:
        research_file = find_latest_research_file(args.genre)
        genre = args.genre
    else:
        # research/配下で一番新しいファイルを使う
        all_files = sorted((PROJECT_ROOT / "research").glob("*.json"), reverse=True)
        research_file = all_files[0] if all_files else None
        genre = research_file.stem.split("_", 1)[1] if research_file else None

    if not research_file:
        print("research/配下にリサーチ結果が見つかりません。先に research_agent.py を実行してください。", file=sys.stderr)
        sys.exit(1)

    data = json.loads(research_file.read_text(encoding="utf-8"))
    items = data.get("items", [])[: args.top]
    fetched_at = data.get("fetched_at", "")[:10]

    out_dir = PROJECT_ROOT / "content_drafts"
    today = date.today().isoformat()

    for i, item in enumerate(items, start=1):
        draft = build_draft(item, genre, fetched_at)
        out_path = out_dir / f"{today}_{genre}_{i}.txt"
        out_path.write_text(draft, encoding="utf-8")

        print(f"\n{'=' * 60}")
        print(f"[{i}] {out_path.name}")
        print("=" * 60)
        print(draft)
        print()
        result = check_text(draft)
        print(format_report(result))


if __name__ == "__main__":
    main()
