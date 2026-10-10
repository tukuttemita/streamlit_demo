"""レビュー分類の処理。

現在はキーワードによる簡易判定のダミー実装です。
後で生成AIの呼び出しに差し替える場合も、関数名・引数・戻り値の形は変えないでください。
注意: レビュー本文や settings のプロンプトは、print / logging などに出力しないこと。
"""

# 分類の選択肢(画面の絞り込みやグラフでも使用する)
SENTIMENTS = ["ポジティブ", "ネガティブ", "中立"]
CATEGORIES = ["品質", "価格", "配送・梱包", "サイズ・デザイン", "使いやすさ", "サポート", "その他"]

# 感情判定用のキーワード(ダミー用)
_POSITIVE_WORDS = [
    "良い", "良く", "良かっ", "よかっ", "最高", "満足", "おすすめ", "気に入", "便利", "素晴らしい",
    "丈夫", "きれい", "綺麗", "おしゃれ", "助かっ", "安い", "お得", "早く", "丁寧", "使いやすい",
    "快適", "好評", "手頃",
]
_NEGATIVE_WORDS = [
    "悪", "残念", "不満", "壊れ", "故障", "破損", "傷", "遅", "高すぎ", "割高", "高い", "返品",
    "がっかり", "不便", "使いにくい", "分かりにくい", "小さすぎ", "大きすぎ", "安っぽ", "ひどい",
    "雑", "不親切", "潰れ",
]

# カテゴリ判定用のキーワード(同点の場合は上にあるカテゴリを優先)
_CATEGORY_WORDS = {
    "配送・梱包": ["配送", "届", "梱包", "包装", "箱", "到着", "発送", "納期"],
    "サポート": ["サポート", "問い合わせ", "問合せ", "対応", "返金", "返品", "交換", "返信", "連絡"],
    "価格": ["価格", "値段", "高い", "高すぎ", "安い", "コスパ", "割高", "お得", "手頃"],
    "サイズ・デザイン": ["サイズ", "大きさ", "小さ", "大き", "デザイン", "色", "見た目", "おしゃれ"],
    "使いやすさ": ["使いやす", "使いにく", "操作", "使い勝手", "便利", "不便", "簡単", "説明書"],
    "品質": ["品質", "壊れ", "故障", "耐久", "丈夫", "作り", "傷", "素材", "安っぽ"],
}

# 要約文のテンプレート(ダミー用。感情ごとに1文)
_SUMMARY_TEMPLATES = {
    "ポジティブ": "{category}について満足の声が寄せられています。",
    "ネガティブ": "{category}に関する不満・改善要望が寄せられています。",
    "中立": "{category}について、強い要望や不満は見られません。",
}


def _judge_sentiment(text: str) -> str:
    """キーワードの出現数で感情を判定する。"""
    pos = sum(text.count(w) for w in _POSITIVE_WORDS)
    neg = sum(text.count(w) for w in _NEGATIVE_WORDS)
    if pos > neg:
        return "ポジティブ"
    if neg > pos:
        return "ネガティブ"
    return "中立"


def _judge_category(text: str) -> str:
    """キーワードの出現数が最も多いカテゴリを返す(該当なしは「その他」)。"""
    best_category, best_score = "その他", 0
    for category, words in _CATEGORY_WORDS.items():
        score = sum(text.count(w) for w in words)
        if score > best_score:
            best_category, best_score = category, score
    return best_category


def analyze_reviews(texts: list[str], settings: dict) -> list[dict]:
    """レビュー本文のリストを分類し、同じ順序・同じ件数の結果リストを返す。

    引数:
        texts: レビュー本文のリスト(呼び出し側がバッチ単位に分けて渡す)
        settings: {"model_name": str, "prompt_template": str, "batch_size": int}
    戻り値:
        [{"sentiment": 感情, "category": カテゴリ, "summary": 要約1文}, ...]

    ダミー実装のため settings は使用しない。
    生成AIに差し替える際は、ここで settings のモデル名とプロンプトを使って呼び出す。
    """
    results = []
    for text in texts:
        sentiment = _judge_sentiment(text)
        category = _judge_category(text)
        results.append(
            {
                "sentiment": sentiment,
                "category": category,
                "summary": _SUMMARY_TEMPLATES[sentiment].format(category=category),
            }
        )
    return results
