"""ログイン中のユーザー情報の取得。

現在は固定値を返すダミー実装です。
後で認証基盤の情報を読む実装に差し替える場合も、戻り値の形は変えないでください。
"""

ROLE_GENERAL = "一般"
ROLE_ADMIN = "管理者"
ROLES = [ROLE_GENERAL, ROLE_ADMIN]


def get_current_user() -> dict:
    """現在のユーザーを {"name": 名前, "role": ロール} の形で返す(固定値)。"""
    return {"name": "サンプルユーザー", "role": ROLE_GENERAL}
