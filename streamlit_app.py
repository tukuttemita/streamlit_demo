"""商品レビュー分析ツール(動作確認用モック)の画面。

外部サービスには接続せず、すべてダミー処理で動作します。
画面の処理だけを持ち、分類・保管・認証は services/ 以下に切り出しています。

注意:
- レビュー本文や設定のプロンプトを print / logging / デバッグ出力に出さないこと。
- レビュー本文を含むデータに st.cache_data を使わないこと(セッション内の session_state のみ使用)。
"""

import io

import altair as alt
import pandas as pd
import streamlit as st

from services import analyzer, auth, storage

st.set_page_config(page_title="商品レビュー分析ツール", layout="wide")

UNSELECTED = "(未選択)"
SENTIMENT_COLORS = {"ポジティブ": "#3b82c4", "ネガティブ": "#d9534f", "中立": "#9aa5b1"}

# 分類用プロンプトの既定文({review} にレビュー本文が入る想定)
DEFAULT_PROMPT = (
    "次の商品レビューを分類してください。\n"
    "- 感情: ポジティブ / ネガティブ / 中立 のいずれか\n"
    "- カテゴリ: 品質 / 価格 / 配送・梱包 / サイズ・デザイン / 使いやすさ / サポート / その他 のいずれか\n"
    "- 要望・不満の要約: 1文で簡潔に\n\n"
    "レビュー:\n{review}"
)
DEFAULT_SETTINGS = {"model_name": "", "prompt_template": DEFAULT_PROMPT, "batch_size": 20}

# 列の割り当てで、列名から候補を推測するためのキーワード
COLUMN_HINTS = {
    "review": ["レビュー本文", "本文", "レビュー", "コメント", "review", "comment", "text"],
    "rating": ["評価", "星", "rating", "star", "score"],
    "date": ["投稿日", "日付", "日時", "date"],
    "product": ["商品名", "商品", "product", "item"],
}


# ---------- 補助関数 ----------

def read_csv_bytes(data: bytes) -> tuple[pd.DataFrame | None, str | None]:
    """CSVのバイト列を読み込む。戻り値は (DataFrame, エラーメッセージ)。"""
    last_error = "CSVを読み込めませんでした。UTF-8またはShift_JISのCSVファイルかご確認ください。"
    for encoding in ("utf-8-sig", "cp932"):  # 文字コードを順に試す
        try:
            df = pd.read_csv(io.BytesIO(data), encoding=encoding, dtype=str)
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            return None, "ファイルが空です。内容のあるCSVファイルを選んでください。"
        except Exception:  # 詳細に本文が含まれる恐れがあるため、内容は表示しない
            return None, last_error
        if df.empty or len(df.columns) == 0:
            return None, "CSVにデータ行がありません。ヘッダー行と1行以上のデータが必要です。"
        return df, None
    return None, last_error


def guess_column(columns: list[str], hints: list[str], used: set) -> str:
    """列名から割り当て候補を推測する(見つからなければ未選択)。"""
    for hint in hints:
        for col in columns:
            if col not in used and hint.lower() in str(col).lower():
                return col
    return UNSELECTED


def escape_formula(value):
    """表計算ソフトで数式として解釈されないよう、先頭の記号を無害化する。"""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """結果をCSV(Excelで開ける BOM 付きUTF-8)のバイト列にする。"""
    safe = df.copy()
    for col in safe.columns:
        if safe[col].dtype == object or pd.api.types.is_string_dtype(safe[col]):
            safe[col] = safe[col].map(escape_formula)
    return safe.to_csv(index=False).encode("utf-8-sig")


# ---------- 状態の初期化 ----------

st.session_state.setdefault("settings", DEFAULT_SETTINGS.copy())
st.session_state.setdefault("file_version", 0)

# ---------- サイドバー ----------

with st.sidebar:
    st.title("商品レビュー分析ツール")
    st.markdown(
        "1. レビューのCSVをアップロードします\n"
        "2. 列を割り当てて「分析を実行」を押します\n"
        "3. 結果を確認し、CSVでダウンロードします"
    )
    st.divider()

    current_user = auth.get_current_user()  # 認証処理(services/auth.py)
    user_box = st.empty()
    # 動作確認用: ロールを切り替えて画面の違いを確認できる
    role = st.selectbox(
        "ロールの切り替え(動作確認用)",
        auth.ROLES,
        index=auth.ROLES.index(current_user["role"]),
    )
    user_box.markdown(f"**現在のユーザー**\n\n{current_user['name']}(ロール: {role})")

is_admin = role == auth.ROLE_ADMIN

# 管理者のみ「設定」タブを表示する
tab_names = ["分析"] + (["設定"] if is_admin else [])
tabs = st.tabs(tab_names)


# ---------- 分析の実行 ----------

def run_analysis(df: pd.DataFrame, cols: dict) -> None:
    """バッチ単位で分析し、進捗を表示しながら結果を session_state に保存する。"""
    settings = st.session_state["settings"]

    # 本文が空の行は対象外にする
    body = df[cols["review"]]
    valid = body.notna() & (body.astype(str).str.strip() != "")
    work = df[valid].reset_index(drop=True)
    skipped = int((~valid).sum())
    if work.empty:
        st.error("レビュー本文が入力されている行がありません。列の割り当てをご確認ください。")
        return

    texts = work[cols["review"]].astype(str).tolist()
    total = len(texts)
    batch_size = max(1, int(settings["batch_size"]))

    bar = st.progress(0.0)
    status = st.empty()
    status.text(f"0/{total}件を処理中")

    results: list[dict] = []
    try:
        for start in range(0, total, batch_size):
            chunk = texts[start : start + batch_size]
            results.extend(analyzer.analyze_reviews(chunk, settings))  # 分類処理(services/analyzer.py)
            done = min(start + batch_size, total)
            bar.progress(done / total)
            status.text(f"{done}/{total}件を処理中")
    except Exception:  # 例外の内容にレビュー本文が含まれる恐れがあるため、表示しない
        bar.empty()
        status.empty()
        st.error("分析中にエラーが発生しました。しばらくしてからもう一度お試しください。")
        return

    if len(results) != total:
        bar.empty()
        status.empty()
        st.error("分析結果の件数が入力と一致しませんでした。分類処理の実装をご確認ください。")
        return
    status.text(f"{total}/{total}件の処理が完了しました")

    # 結果表を組み立てる
    out = pd.DataFrame(
        {
            "レビュー本文": work[cols["review"]],
            "感情": [r["sentiment"] for r in results],
            "カテゴリ": [r["category"] for r in results],
            "要望・不満の要約": [r["summary"] for r in results],
        }
    )
    notices = []
    if cols["product"]:
        out["商品"] = work[cols["product"]]
    if cols["rating"]:
        rating = pd.to_numeric(work[cols["rating"]], errors="coerce")
        if rating.notna().any():
            out["評価"] = rating
        else:
            notices.append("評価の列を数値として読み取れなかったため、平均評価は表示しません。")
    if cols["date"]:
        posted = pd.to_datetime(work[cols["date"]], errors="coerce", format="mixed")
        if posted.notna().any():
            out["投稿日"] = posted.dt.date
        else:
            notices.append("投稿日の列を日付として読み取れなかったため、推移グラフは表示しません。")

    st.session_state["result"] = {"df": out, "skipped": skipped, "notices": notices}


# ---------- 結果の表示 ----------

def show_results(result: dict) -> None:
    """指標・グラフ・結果表・ダウンロードボタンを表示する。"""
    df = result["df"]
    total = len(df)

    if result["skipped"]:
        st.info(f"レビュー本文が空の {result['skipped']} 行は分析の対象外にしました。")
    for message in result["notices"]:
        st.warning(message)

    st.subheader("分析結果")
    st.caption("指標とグラフは全件、結果の表とCSVは絞り込み後の内容です。")

    # 指標タイル
    has_rating = "評価" in df.columns
    metric_cols = st.columns(4 if has_rating else 3)
    metric_cols[0].metric("総件数", f"{total:,}件")
    metric_cols[1].metric("ポジティブ率", f"{(df['感情'] == 'ポジティブ').mean():.1%}")
    metric_cols[2].metric("ネガティブ率", f"{(df['感情'] == 'ネガティブ').mean():.1%}")
    if has_rating:
        metric_cols[3].metric("平均評価", f"{df['評価'].mean():.2f}")

    # グラフ
    has_date = "投稿日" in df.columns
    chart_cols = st.columns(3 if has_date else 2)

    with chart_cols[0]:
        st.markdown("**感情の割合**")
        sentiment_df = (
            df["感情"].value_counts().reindex(analyzer.SENTIMENTS, fill_value=0).rename_axis("感情").reset_index(name="件数")
        )
        pie = (
            alt.Chart(sentiment_df)
            .mark_arc(innerRadius=50)
            .encode(
                theta=alt.Theta("件数:Q"),
                color=alt.Color(
                    "感情:N",
                    scale=alt.Scale(domain=list(SENTIMENT_COLORS), range=list(SENTIMENT_COLORS.values())),
                    legend=alt.Legend(title=None),
                ),
                tooltip=["感情", "件数"],
            )
        )
        st.altair_chart(pie)

    with chart_cols[1]:
        st.markdown("**カテゴリ別の件数**")
        category_df = (
            df["カテゴリ"].value_counts().reindex(analyzer.CATEGORIES, fill_value=0).rename_axis("カテゴリ").reset_index(name="件数")
        )
        bars = (
            alt.Chart(category_df)
            .mark_bar(color="#3b82c4")
            .encode(
                x=alt.X("件数:Q", title=None),
                y=alt.Y("カテゴリ:N", sort=analyzer.CATEGORIES, title=None),
                tooltip=["カテゴリ", "件数"],
            )
        )
        st.altair_chart(bars)

    if has_date:
        with chart_cols[2]:
            st.markdown("**投稿日ごとの件数推移**")
            daily = df["投稿日"].dropna().value_counts().sort_index()
            st.line_chart(daily)

    # 絞り込み
    st.markdown("**絞り込み**")
    f1, f2, f3 = st.columns([1, 1, 2])
    sel_sentiments = f1.multiselect("感情", analyzer.SENTIMENTS, default=analyzer.SENTIMENTS)
    sel_categories = f2.multiselect("カテゴリ", analyzer.CATEGORIES, default=analyzer.CATEGORIES)
    keyword = f3.text_input("キーワード検索(レビュー本文)")

    filtered = df[df["感情"].isin(sel_sentiments) & df["カテゴリ"].isin(sel_categories)]
    if keyword.strip():
        filtered = filtered[
            filtered["レビュー本文"].str.contains(keyword.strip(), case=False, regex=False, na=False)
        ]

    # 結果の表
    st.write(f"該当 {len(filtered):,}件 / 全 {total:,}件")
    if filtered.empty:
        st.info("条件に一致するレビューがありません。絞り込みの条件を変更してください。")
    else:
        st.dataframe(filtered, hide_index=True, width="stretch")

    # ダウンロード(押下時に結果の保管処理も呼ぶ。services/storage.py)
    st.download_button(
        "結果をCSVでダウンロード",
        data=to_csv_bytes(filtered),
        file_name="review_result.csv",
        mime="text/csv",
        disabled=filtered.empty,
        on_click=storage.save_result,
        args=(filtered, "review_result.csv"),
    )


# ---------- タブ1: 分析 ----------

with tabs[0]:
    uploaded = st.file_uploader("レビューのCSVファイルをアップロード(1ファイル)", type=["csv"])

    if uploaded is None:
        # ファイルが外されたら、前回の内容を破棄する
        for key in ("csv_df", "file_sig", "result"):
            st.session_state.pop(key, None)
        st.info("CSVファイルをアップロードすると、ここにプレビューが表示されます。")
    else:
        data = uploaded.getvalue()
        signature = (uploaded.name, len(data))

        # 新しいファイルが選ばれたときだけ読み込み直す
        if st.session_state.get("file_sig") != signature:
            st.session_state.pop("result", None)
            st.session_state["file_version"] += 1
            df_loaded, error = read_csv_bytes(data)
            st.session_state["file_sig"] = signature
            st.session_state["csv_df"] = df_loaded
            st.session_state["csv_error"] = error
            if df_loaded is not None:
                try:
                    storage.save_upload(data, uploaded.name)  # 保管処理(services/storage.py)
                except Exception:
                    st.warning("アップロードしたファイルの保管に失敗しました。分析は続けられます。")

        csv_df = st.session_state.get("csv_df")
        if csv_df is None:
            st.error(st.session_state.get("csv_error") or "CSVを読み込めませんでした。")
        else:
            st.subheader("プレビュー(先頭5行)")
            st.caption(f"全 {len(csv_df):,}行 / {len(csv_df.columns)}列")
            st.dataframe(csv_df.head(5), hide_index=True, width="stretch")

            # 列の割り当て
            st.subheader("列の割り当て")
            columns = [str(c) for c in csv_df.columns]
            options = [UNSELECTED] + columns
            version = st.session_state["file_version"]
            used: set = set()
            defaults = {}
            for name in ("review", "rating", "date", "product"):
                guessed = guess_column(columns, COLUMN_HINTS[name], used)
                used.add(guessed)
                defaults[name] = options.index(guessed)

            c1, c2, c3, c4 = st.columns(4)
            picked = {
                "review": c1.selectbox("レビュー本文(必須)", options, index=defaults["review"], key=f"col_review_{version}"),
                "rating": c2.selectbox("評価の星(任意)", options, index=defaults["rating"], key=f"col_rating_{version}"),
                "date": c3.selectbox("投稿日(任意)", options, index=defaults["date"], key=f"col_date_{version}"),
                "product": c4.selectbox("商品名または商品ID(任意)", options, index=defaults["product"], key=f"col_product_{version}"),
            }

            if st.button("分析を実行", type="primary"):
                chosen = [v for v in picked.values() if v != UNSELECTED]
                if picked["review"] == UNSELECTED:
                    st.error("「レビュー本文」の列を選択してください。")
                elif len(chosen) != len(set(chosen)):
                    st.error("同じ列を複数の項目に割り当てることはできません。列の割り当てをご確認ください。")
                else:
                    run_analysis(csv_df, {k: (None if v == UNSELECTED else v) for k, v in picked.items()})

    # 結果は session_state に保持するので、絞り込み操作でも再分析されない
    if st.session_state.get("result") is not None and uploaded is not None:
        show_results(st.session_state["result"])


# ---------- タブ2: 設定(管理者のみ) ----------

if is_admin:
    with tabs[1]:
        st.subheader("分類の設定")
        saved = st.session_state["settings"]
        with st.form("settings_form"):
            model_name = st.text_input("使用するモデル名", value=saved["model_name"], placeholder="model-name")
            prompt_template = st.text_area("分類用プロンプトのテンプレート", value=saved["prompt_template"], height=260)
            batch_size = st.number_input("一度に処理する件数", min_value=1, max_value=1000, value=int(saved["batch_size"]), step=1)
            submitted = st.form_submit_button("保存")
        if submitted:
            # 現在は st.session_state に保存するだけ(ブラウザを閉じると消える)
            st.session_state["settings"] = {
                "model_name": model_name.strip(),
                "prompt_template": prompt_template,
                "batch_size": int(batch_size),
            }
            st.success("設定を保存しました。")
