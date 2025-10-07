# pydantic-touchall

PydanticのBaseModelで未使用フィールドを検出するlinterツール

## 機能

- BaseModelの未使用フィールドを検出
- 必須フィールドの未使用をエラーとして報告
- Optionalフィールドの未使用をエラーとして報告
- 辞書型フィールドの検出

## インストール

```bash
uv add pydantic-touchall
```

開発環境でのセットアップ

```bash
git clone https://github.com/po3rin/pydantic-touchall.git
cd pydantic-touchall
uv sync --dev
```

## 使用方法

### コマンドライン

```bash
pydantic-touchall path/to/your/file.py

# 複数ファイルのチェック
pydantic-touchall file1.py file2.py file3.py

# ワイルドカードを使用したファイル指定
pydantic-touchall examples/*.py
pydantic-touchall src/**/*.py

# strictモードで必須フィールドのみチェック
pydantic-touchall --strict file.py
```

### 例

```python
from pydantic import BaseModel
from typing import Optional


class User(BaseModel):
    name: str
    email: str
    age: int
    address: Optional[str] = None
    nickname: str = "Anonymous"


# NG: ageが未使用
user = User(
    name="Alice",
    email="alice@example.com",
)

# OK: すべてのフィールドを使用
user2 = User(
    name="Bob",
    email="bob@example.com",
    age=30,
    address="Tokyo",
    nickname="Bob123"
)
```

linterを実行すると以下のような結果が表示されます：

```
examples/test_models.py:
  14:13 - Error: Userの必須フィールドが不足: age
  14:13 - Error: Userのオプションフィールドが未使用: address, nickname

  2 つのエラーが検出されました
```

## テスト

### 単体テスト

```bash
uv run pytest tests/ -v
```

### サンプルファイルでの動作確認

```bash
uv run pydantic-touchall examples/test_models.py
```

## エラーレベル

1. **必須フィールドの未使用** (Error): デフォルト値なしの必須フィールドが未使用の場合
2. **辞書型フィールドの未使用** (Error): 辞書型フィールドが未使用の場合
3. **オプションフィールドの未使用** (Error): Optionalやデフォルト値ありのフィールドが未使用の場合

**kwargsが使用されている場合は、チェックをスキップします。

## ignoreコメント

他のlinterと同様に、コメントを使ってチェックを無視することができます。

### 全体を無視

```python
# pydantic-touchall: ignore
user = User(
    name="Alice",
    # ageを省略してもエラーにならない
)

# 短縮形も使用可能
user = User(  # touchall: ignore
    name="Alice",
)
```

### 特定のフィールドのみ無視

```python
# ageのみチェックを無視
user = User(  # pydantic-touchall: ignore-field age
    name="Alice",
    email="alice@example.com",
)

# 複数フィールドを無視（カンマ区切り）
user = User(  # pydantic-touchall: ignore-field age, address
    name="Alice",
    email="alice@example.com",
)

# 短縮形も使用可能
user = User(  # touchall: ignore-field age
    name="Alice",
    email="alice@example.com",
)
```

### コメントの位置

コメントはインスタンス化の行、または直前の行に記述できます。

```python
# pydantic-touchall: ignore
user = User(
    name="Alice",
)

# または
user = User(  # pydantic-touchall: ignore
    name="Alice",
)
```

## ライセンス

MIT