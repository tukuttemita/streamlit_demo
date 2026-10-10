"""ファイルの保管処理。

現在は何も保存しない(保存したふりをするだけ)ダミー実装です。
後でクラウドのストレージに差し替える場合も、関数名と引数は変えないでください。
"""

import pandas as pd


def save_upload(file_bytes: bytes, filename: str) -> dict:
    """アップロードされたCSVを保管する(現在は何もしない)。

    戻り値: 保管先を表す辞書(ダミー)。
    差し替え時の注意: filename は利用者の入力なので、そのままパスに使わず、
    サーバー側で生成したキーで保管すること。
    """
    return {"saved": False, "location": "dummy://uploads/(not-saved)"}


def save_result(df: pd.DataFrame, filename: str) -> dict:
    """分析結果を保管する(現在は何もしない)。

    戻り値: 保管先を表す辞書(ダミー)。
    """
    return {"saved": False, "location": "dummy://results/(not-saved)"}
