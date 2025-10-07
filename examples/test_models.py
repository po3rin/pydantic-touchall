from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    name: str
    email: str
    age: int
    address: Optional[str] = None
    nickname: str = "Anonymous"


# エラーケース1: 必須フィールドが不足
user_error1 = User(
    name="Alice",
    email="alice@example.com",
    # ageが不足!
)

# エラーケース2: オプションフィールドも未使用
user_error2 = User(
    name="Bob",
    email="bob@example.com",
    age=30,
    # address と nickname が未使用
)

# OKケース: 全フィールド設定
user_ok = User(
    name="Charlie",
    email="charlie@example.com",
    age=25,
    address="Tokyo",
    nickname="Charlie123"
)

# ignoreコメントの例1: 全体を無視
user_ignore_all = User(  # pydantic-touchall: ignore
    name="Dave",
    email="dave@example.com",
    # 必須フィールドが不足していても無視される
)

# ignoreコメントの例2: 特定のフィールドのみ無視
user_ignore_field = User(  # pydantic-touchall: ignore-field age
    name="Eve",
    email="eve@example.com",
    # ageは無視されるが、addressとnicknameはエラー
)

# ignoreコメントの例3: 複数フィールドを無視
user_ignore_multiple = User(  # touchall: ignore-field age, address
    name="Frank",
    email="frank@example.com",
    # ageとaddressは無視されるが、nicknameはエラー
)

# **kwargsの例: チェックがスキップされる
data = {
    "name": "Grace",
    "email": "grace@example.com",
    "age": 28,
}
user_kwargs = User(**data)  # **kwargsの場合はチェックをスキップ
