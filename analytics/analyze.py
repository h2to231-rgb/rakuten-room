"""
分析Agent: 日々の実績（フォロワー数・いいね数・クリック数・成果など）を記録し、
docs/03_kpi_framework.md の目標値と比較して、ジャンル別の傾向・ローテーション調整案をまとめる。

実績データはROOM管理画面・楽天アフィリエイト管理画面から人間が確認し、
`log`コマンドで記録する（自動取得のAPIがないため、ここは人間の入力が必要）。

使い方:
    # 実績を1件記録する（投稿した日ごとに実行）
    python analytics/analyze.py log --date 2026-08-24 --genre beauty \
        --followers 12 --posts 1 --likes 3 --clicks 0 --conversions 0 --revenue 0 --notes "初日"

    # これまでの記録を集計してレポートを出す
    python analytics/analyze.py report
"""

import argparse
import csv
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = PROJECT_ROOT / "analytics" / "metrics_log.csv"

FIELDS = [
    "date", "genre", "followers_total", "posts_count",
    "total_likes", "clicks", "conversions", "revenue_jpy", "notes",
]

# docs/03_kpi_framework.md の「初期目標値」表に対応（週番号 -> (フォロワー累計増min, max, 投稿あたり平均いいねmin, max)）
WEEK_TARGETS = {
    1: (5, 10, 1, 3),
    2: (10, 20, 2, 4),
    4: (30, 50, 3, 6),
    6: (60, 100, 5, 10),
}


def load_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for r in rows:
        r["_date"] = datetime.strptime(r["date"], "%Y-%m-%d").date()
        for key in ("followers_total", "posts_count", "total_likes", "clicks", "conversions", "revenue_jpy"):
            r[key] = float(r[key]) if r.get(key) not in (None, "") else 0.0
    rows.sort(key=lambda r: r["_date"])
    return rows


def log_entry(args):
    LOG_PATH.parent.mkdir(exist_ok=True)
    is_new = not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0
    with open(LOG_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "date": args.date,
                "genre": args.genre,
                "followers_total": args.followers,
                "posts_count": args.posts,
                "total_likes": args.likes,
                "clicks": args.clicks,
                "conversions": args.conversions,
                "revenue_jpy": args.revenue,
                "notes": args.notes or "",
            }
        )
    print(f"記録しました: {args.date} / {args.genre} / フォロワー累計{args.followers}")


def week_index(start: date, d: date) -> int:
    return (d - start).days // 7 + 1


def build_report(rows: list[dict]) -> str:
    if not rows:
        return (
            "まだ実績データがありません。\n"
            "投稿を開始したら、次のように記録してください:\n"
            "  python analytics/analyze.py log --date YYYY-MM-DD --genre <genre> "
            "--followers <累計フォロワー数> --posts 1 --likes <いいね数> "
            "--clicks <クリック数> --conversions <成果件数> --revenue <成果報酬額>"
        )

    start = rows[0]["_date"]
    lines = [f"# 分析レポート（{rows[0]['date']} 〜 {rows[-1]['date']}、記録{len(rows)}件）", ""]

    # 週ごとの集計
    weekly = defaultdict(list)
    for r in rows:
        weekly[week_index(start, r["_date"])].append(r)

    lines.append("## 週次サマリー")
    for wk in sorted(weekly):
        wk_rows = weekly[wk]
        followers_start = wk_rows[0]["followers_total"]
        followers_end = wk_rows[-1]["followers_total"]
        followers_delta = followers_end - (rows[0]["followers_total"] if wk == 1 else weekly[wk - 1][-1]["followers_total"] if (wk - 1) in weekly else followers_start)
        total_posts = sum(r["posts_count"] for r in wk_rows)
        total_likes = sum(r["total_likes"] for r in wk_rows)
        avg_likes = total_likes / total_posts if total_posts else 0

        target = WEEK_TARGETS.get(wk)
        target_str = ""
        if target:
            f_min, f_max, l_min, l_max = target
            f_status = "✅" if followers_delta >= f_min else "⚠️"
            l_status = "✅" if avg_likes >= l_min else "⚠️"
            target_str = (
                f"（目標: フォロワー+{f_min}〜{f_max} {f_status} / 平均いいね{l_min}〜{l_max} {l_status}）"
            )

        lines.append(
            f"- 週{wk}: フォロワー+{followers_delta:.0f} / 投稿{total_posts:.0f}本 / "
            f"平均いいね{avg_likes:.1f} {target_str}"
        )

    # ジャンル別集計
    lines.append("\n## ジャンル別サマリー")
    by_genre = defaultdict(list)
    for r in rows:
        by_genre[r["genre"]].append(r)

    genre_perf = []
    for genre, g_rows in by_genre.items():
        total_posts = sum(r["posts_count"] for r in g_rows)
        total_likes = sum(r["total_likes"] for r in g_rows)
        total_clicks = sum(r["clicks"] for r in g_rows)
        total_conversions = sum(r["conversions"] for r in g_rows)
        total_revenue = sum(r["revenue_jpy"] for r in g_rows)
        avg_likes = total_likes / total_posts if total_posts else 0
        genre_perf.append((genre, avg_likes, total_posts, total_clicks, total_conversions, total_revenue))
        lines.append(
            f"- {genre}: 投稿{total_posts:.0f}本 / 平均いいね{avg_likes:.1f} / "
            f"クリック{total_clicks:.0f} / 成果{total_conversions:.0f}件 / 報酬¥{total_revenue:.0f}"
        )

    # ローテーション調整の提案
    if len(genre_perf) >= 2:
        genre_perf.sort(key=lambda x: x[1], reverse=True)
        best = genre_perf[0]
        worst = genre_perf[-1]
        if best[2] >= 3 and worst[2] >= 3:  # ある程度投稿数が溜まっている場合のみ提案
            lines.append(
                f"\n## 提案\n"
                f"「{best[0]}」が平均いいね{best[1]:.1f}で最も反応が良く、"
                f"「{worst[0]}」が{worst[1]:.1f}で最も低い結果です。"
                f"docs/02_genre_test_plan.mdのローテーション比率を「{best[0]}」寄りに調整することを検討してください。"
            )
        else:
            lines.append("\n## 提案\n各ジャンルの投稿数がまだ少ないため、判断は次回以降に持ち越します。")

    return "\n".join(lines)


def cmd_report(args):
    rows = load_log()
    report = build_report(rows)
    print(report)

    out_path = PROJECT_ROOT / "reports" / "analysis_latest.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"\n(レポートを {out_path.relative_to(PROJECT_ROOT)} にも保存しました)")


def main():
    parser = argparse.ArgumentParser(description="楽天ROOM 分析Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    p_log = sub.add_parser("log", help="1日分の実績を記録する")
    p_log.add_argument("--date", required=True, help="YYYY-MM-DD")
    p_log.add_argument("--genre", required=True, choices=["gadget", "beauty", "kitchen"])
    p_log.add_argument("--followers", type=float, required=True, help="その日時点のフォロワー累計数")
    p_log.add_argument("--posts", type=float, default=1, help="その日の投稿数")
    p_log.add_argument("--likes", type=float, default=0, help="その日の投稿の合計いいね数")
    p_log.add_argument("--clicks", type=float, default=0, help="クリック数（わかる範囲で）")
    p_log.add_argument("--conversions", type=float, default=0, help="成果件数")
    p_log.add_argument("--revenue", type=float, default=0, help="成果報酬額(円)")
    p_log.add_argument("--notes", default="", help="メモ")
    p_log.set_defaults(func=log_entry)

    p_report = sub.add_parser("report", help="これまでの記録を集計してレポートを出す")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
