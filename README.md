# 商品レビュー分析ツール(動作確認用モック)

Streamlit で動く、ダミー処理のみの画面です。外部サービスには接続しません。

## 起動方法

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

ブラウザで http://localhost:8501 を開きます。

## サンプルCSVの作成

```bash
python sample_data.py
```

`sample_reviews.csv` が生成されます。画面からアップロードして動作を確認できます。
