"""
PR表記・優良誤認/有利誤認チェッカー（簡易ルールベース）

docs/04_pr_disclosure_guidelines.md のルールに基づき、投稿下書きテキストを機械的にチェックする。
あくまで一次スクリーニング。最終判断は必ず人間が行うこと（誤検知・見逃しがあり得る）。

使い方:
    python compliance/pr_checker.py content_drafts/2026-08-24_beauty.txt
    echo "本文テキスト" | python compliance/pr_checker.py -
"""

import argparse
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")

# いずれかが本文に含まれていればPR表記ありとみなす
PR_MARKERS = [
    "PR】",
    "[PR]",
    "＃PR",
    "#PR",
    "アフィリエイトリンク",
    "紹介料",
    "報酬が発生",
    "広告を含み",
]

# カテゴリ: (説明, 正規表現パターン一覧)
NG_PATTERNS = {
    "優良誤認(断定的な効果表現)": [
        r"絶対に?痩せ",
        r"必ず(改善|治る|効果)",
        r"医学的に(証明|実証)",
        r"副作用(なし|ゼロ)",
        r"100+\s*%\s*(安全|効果)",
        r"誰でも簡単に.{0,6}痩せ",
        r"完治",
    ],
    "有利誤認(価格・期間の誇張、要ファクトチェック)": [
        r"今だけ",
        r"本日限り",
        r"残りわずか",
        r"数量限定",
    ],
    "根拠不明のNo.1表現(出典明記の有無を確認)": [
        r"業界No\.?1",
        r"売上(日本一|世界一)",
        r"(業界|日本|世界)(で)?一番",
    ],
}


def check_text(text: str) -> dict:
    has_pr = any(marker in text for marker in PR_MARKERS)

    findings = []
    for category, patterns in NG_PATTERNS.items():
        for pattern in patterns:
            for m in re.finditer(pattern, text):
                findings.append(
                    {
                        "category": category,
                        "matched": m.group(),
                        "position": m.start(),
                    }
                )

    return {
        "has_pr_disclosure": has_pr,
        "findings": findings,
    }


def format_report(result: dict) -> str:
    lines = []
    lines.append("=== PR表記チェック ===")
    lines.append("✅ PR表記あり" if result["has_pr_disclosure"] else "❌ PR表記が見つかりません。docs/04_pr_disclosure_guidelines.md の定型文を追加してください。")

    lines.append("\n=== 要注意フレーズ ===")
    if not result["findings"]:
        lines.append("該当なし")
    else:
        for f in result["findings"]:
            lines.append(f"- [{f['category']}] 「{f['matched']}」(位置: {f['position']}文字目) ※文脈を確認し、事実と異なる場合は修正してください")

    lines.append("\n※このチェックは一次スクリーニングです。最終判断は必ず人間が行ってください。")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="投稿下書きのPR表記・誇大表現チェッカー")
    parser.add_argument("path", help="チェック対象のテキストファイルパス（'-'で標準入力）")
    args = parser.parse_args()

    if args.path == "-":
        text = sys.stdin.read()
    else:
        with open(args.path, encoding="utf-8") as f:
            text = f.read()

    result = check_text(text)
    print(format_report(result))

    if not result["has_pr_disclosure"] or result["findings"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
