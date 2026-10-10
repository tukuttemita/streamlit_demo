"""動作確認用のダミーレビューCSV(sample_reviews.csv)を生成するスクリプト。

使い方: python sample_data.py
すべて架空の内容です。実在の企業名・ブランド名・商品名・人名は含みません。
"""

import random
from datetime import date, timedelta

import pandas as pd

OUTPUT_FILE = "sample_reviews.csv"
ROW_COUNT = 100
SEED = 42  # 毎回同じ内容になるように固定

# 架空の商品名
PRODUCTS = ["サンプル商品A", "サンプル商品B", "サンプル商品C"]

# カテゴリ × 感情ごとのレビュー文のひな形
REVIEWS = {
    "品質": {
        "pos": [
            "品質がとても良く、作りもしっかりしていて満足です。",
            "丈夫で長く使えそうです。素材も良いと感じました。",
            "作りが丁寧で、細部まで気に入っています。",
        ],
        "neg": [
            "届いてすぐ壊れてしまい、残念でした。品質に不満です。",
            "素材が安っぽく、傷もついていてがっかりしました。",
            "数週間で故障しました。耐久性に不満があります。",
        ],
        "neu": [
            "素材は一般的なもので、可もなく不可もなくといった印象です。",
            "品質は普通だと思います。",
        ],
    },
    "価格": {
        "pos": [
            "価格が手頃でお得に買えました。満足です。",
            "値段が安いのに満足できる内容でした。",
        ],
        "neg": [
            "値段が高すぎると感じました。割高な印象で残念です。",
            "価格が高すぎます。もう少し安くしてほしいです。",
        ],
        "neu": [
            "価格は相場どおりだと思います。",
            "値段は普通で、妥当な範囲だと思います。",
        ],
    },
    "配送・梱包": {
        "pos": [
            "配送が早く、梱包も丁寧で助かりました。",
            "注文の翌日に届きました。梱包もしっかりしていて満足です。",
        ],
        "neg": [
            "配送が遅れて、予定より届くのが遅く不満でした。",
            "箱が潰れていて、梱包が雑でがっかりしました。",
            "到着までに時間がかかり、配送の遅れが残念でした。",
        ],
        "neu": [
            "通常どおりに届きました。梱包は標準的です。",
            "発送から到着まで数日かかりました。",
        ],
    },
    "サイズ・デザイン": {
        "pos": [
            "デザインがおしゃれで、サイズもちょうど良く気に入っています。",
            "色合いがきれいで、見た目も満足です。",
        ],
        "neg": [
            "思ったより小さすぎて、サイズが合いませんでした。残念です。",
            "写真と色が違っていて、デザインにがっかりしました。",
        ],
        "neu": [
            "サイズは表記どおりでした。デザインはシンプルです。",
        ],
    },
    "使いやすさ": {
        "pos": [
            "操作が簡単で使いやすく、とても便利です。",
            "説明書がわかりやすく、すぐ使えました。使い勝手も良いです。",
        ],
        "neg": [
            "操作が分かりにくく、使いにくいと感じました。不便です。",
            "説明書が不親切で、使い勝手が悪いです。",
        ],
        "neu": [
            "操作は標準的で、説明書を読みながら使っています。",
        ],
    },
    "サポート": {
        "pos": [
            "問い合わせへの対応が丁寧で、すぐ交換してもらえて助かりました。",
            "サポートの連絡が早く、満足しています。",
        ],
        "neg": [
            "問い合わせても返信がなく、対応が悪くて最悪でした。",
            "返品の連絡をしたが対応が遅く、不満です。",
        ],
        "neu": [
            "問い合わせをして、数日後に返信がありました。",
        ],
    },
    "その他": {
        "pos": [
            "家族にも好評で、買ってよかったです。",
            "全体的に満足しています。おすすめです。",
        ],
        "neg": [
            "期待していたほどではなく、がっかりしました。",
            "全体的に不満が残りました。",
        ],
        "neu": [
            "まだ使い始めたばかりなので、評価は保留です。",
            "普通です。",
        ],
    },
}

# 感情の出現割合と、星評価の候補
SENTIMENT_WEIGHTS = {"pos": 50, "neg": 30, "neu": 20}
STAR_CHOICES = {"pos": [5, 5, 4, 4, 4], "neg": [1, 1, 2, 2, 3], "neu": [3, 3, 3, 2, 4]}


def build_rows(rng: random.Random) -> list[dict]:
    """ダミーのレビュー行を ROW_COUNT 件作る。"""
    start = date(2026, 4, 1)
    span_days = 183  # 4月1日〜9月30日
    rows = []
    for _ in range(ROW_COUNT):
        sentiment = rng.choices(list(SENTIMENT_WEIGHTS), weights=list(SENTIMENT_WEIGHTS.values()))[0]
        category = rng.choice(list(REVIEWS))
        rows.append(
            {
                "レビュー本文": rng.choice(REVIEWS[category][sentiment]),
                "評価": rng.choice(STAR_CHOICES[sentiment]),
                "投稿日": (start + timedelta(days=rng.randrange(span_days))).isoformat(),
                "商品名": rng.choices(PRODUCTS, weights=[5, 3, 2])[0],
            }
        )
    return rows


def main() -> None:
    rng = random.Random(SEED)
    df = pd.DataFrame(build_rows(rng)).sort_values("投稿日").reset_index(drop=True)
    # Excelで開いても文字化けしないよう BOM 付きUTF-8で保存する
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"{OUTPUT_FILE} を作成しました({len(df)}件)")


if __name__ == "__main__":
    main()
