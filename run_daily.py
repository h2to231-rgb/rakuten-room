"""
デイリー運用スクリプト: リサーチAgent → ライティングAgent → コンプラチェックを1コマンドで実行し、
その日の投稿候補を reports/ にまとめる。

投稿の実行（ROOMへの実際の投稿操作）はここでは行わない。楽天ROOM利用規約により、
投稿は必ず人間が行う必要があるため、レポートを見て1つ選び、手動で投稿すること。

使い方:
    python run_daily.py
    python run_daily.py --genre kitchen --top 3
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "research"))
sys.path.insert(0, str(PROJECT_ROOT / "content_drafts"))
sys.path.insert(0, str(PROJECT_ROOT / "compliance"))
sys.stdout.reconfigure(encoding="utf-8")

import research_agent  # noqa: E402
import writing_agent  # noqa: E402
from pr_checker import check_text  # noqa: E402


def resolve_genre(genre_arg: str | None) -> str:
    genre = genre_arg or research_agent.WEEKDAY_GENRE.get(date.today().weekday(), "gadget")
    if genre == "summary":
        genre = research_agent.WEEKDAY_GENRE.get((date.today().weekday() - 1) % 7, "gadget")
    return genre


def build_report(genre: str, drafts: list[dict]) -> str:
    today = date.today().isoformat()
    lines = [
        f"# {today} 投稿候補レポート（ジャンル: {genre}）",
        "",
        "この中から1つ選び、内容を確認した上でROOMアプリ/サイトから**手動で**投稿してください。",
        "（楽天ROOM利用規約により、投稿の実行は人間が行う必要があります）",
        "",
        f"- KPI目標: [docs/03_kpi_framework.md](../docs/03_kpi_framework.md)",
        f"- PR表記ルール: [docs/04_pr_disclosure_guidelines.md](../docs/04_pr_disclosure_guidelines.md)",
        "",
        "---",
        "",
    ]

    for i, d in enumerate(drafts, start=1):
        check = d["check"]
        ok = check["has_pr_disclosure"] and not check["findings"]
        status = "✅ 問題なし" if ok else "⚠️ 要確認"
        name = (d["item"].get("itemName") or "")[:50]
        lines.append(f"## 案{i}: {name} [{status}]")
        lines.append("")
        lines.append(f"- 価格: ¥{d['item'].get('itemPrice')}")
        lines.append(f"- レビュー: {d['item'].get('reviewCount')}件（評価{d['item'].get('reviewAverage')}）")
        lines.append(f"- ドラフトファイル: `{d['path'].relative_to(PROJECT_ROOT)}`")
        if check["findings"]:
            matched = ", ".join(f"「{f['matched']}」({f['category']})" for f in check["findings"])
            lines.append(f"- ⚠️ コンプラチェック指摘: {matched}")
        lines.append("")
        lines.append("```")
        lines.append(d["draft"])
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="楽天ROOM デイリー運用（リサーチ→ライティング→コンプラチェック）")
    parser.add_argument("--genre", choices=list(research_agent.GENRE_KEYWORDS), help="ジャンルを指定（省略時は曜日から自動判定）")
    parser.add_argument("--top", type=int, default=3, help="投稿候補として作るドラフト数")
    args = parser.parse_args()

    genre = resolve_genre(args.genre)
    today = date.today().isoformat()

    print(f"[1/3] リサーチ中... (ジャンル: {genre})")
    result = research_agent.run_research(genre, top_n=max(args.top, 10))
    research_path = PROJECT_ROOT / "research" / f"{today}_{genre}.json"
    research_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> {result['item_count']}件取得 ({research_path.relative_to(PROJECT_ROOT)})")

    print("[2/3] ドラフト生成 + コンプラチェック中...")
    items = result["items"][: args.top]
    if not items:
        print("該当する商品が見つかりませんでした。処理を終了します。", file=sys.stderr)
        sys.exit(1)

    drafts = []
    for i, item in enumerate(items, start=1):
        draft = writing_agent.build_draft(item, genre, result["fetched_at"][:10])
        draft_path = PROJECT_ROOT / "content_drafts" / f"{today}_{genre}_{i}.txt"
        draft_path.write_text(draft, encoding="utf-8")
        check = check_text(draft)
        drafts.append({"path": draft_path, "item": item, "draft": draft, "check": check})
        print(f"  [{i}] {draft_path.name} -> {'OK' if check['has_pr_disclosure'] and not check['findings'] else '要確認'}")

    print("[3/3] レポート作成中...")
    report_text = build_report(genre, drafts)
    report_path = PROJECT_ROOT / "reports" / f"{today}.md"
    report_path.write_text(report_text, encoding="utf-8")

    print(f"\n完了。レポート: {report_path.relative_to(PROJECT_ROOT)}")
    print("この中から1つ選んで、楽天ROOMアプリ/サイトから手動で投稿してください。")


if __name__ == "__main__":
    main()
