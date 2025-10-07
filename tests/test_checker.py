"""チェッカーのテスト"""
import tempfile
from pathlib import Path
import pytest
from pydantic_touchall.checker import check_file


def test_missing_required_field():
    """必須フィールドが不足している場合のテスト"""
    code = '''
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

# ageが不足
user = User(
    name="Alice",
    email="alice@example.com",
)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # 必須フィールドageが不足しているエラーがあるはず
        assert len(errors) > 0
        assert any("age" in err[2] for err in errors)
        assert any("Error:" in err[2] for err in errors)

        Path(f.name).unlink()


def test_all_fields_provided():
    """全フィールドが設定されている場合のテスト"""
    code = '''
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

# 全フィールド設定
user = User(
    name="Alice",
    email="alice@example.com",
    age=30,
)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # エラーは含まれないはず
        error_messages = [err[2] for err in errors if err[2].startswith("Error:")]
        assert len(error_messages) == 0

        Path(f.name).unlink()


def test_optional_field():
    """Optionalフィールドの場合のテスト"""
    code = '''
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    name: str
    address: Optional[str] = None

# addressは省略可能
user = User(
    name="Alice",
)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # オプションフィールドが未使用の場合、エラーが報告される（厳密チェック）
        assert len(errors) == 1
        assert any("address" in err[2] for err in errors)
        assert any("オプションフィールドが未使用" in err[2] for err in errors)

        Path(f.name).unlink()


def test_unknown_field():
    """存在しないフィールドを指定した場合のテスト"""
    code = '''
from pydantic import BaseModel

class User(BaseModel):
    name: str

# unknown_fieldは存在しない
user = User(
    name="Alice",
    unknown_field="test",
)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # 存在しないフィールドのエラーがあるはず
        assert len(errors) > 0
        assert any("unknown_field" in err[2] for err in errors)
        assert any("存在しないフィールド" in err[2] for err in errors)

        Path(f.name).unlink()


def test_kwargs_warning():
    """**kwargsを使用した場合のテスト"""
    code = '''
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str

data = {"name": "Alice", "email": "alice@example.com"}
user = User(**data)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # **kwargsの場合はチェックをスキップするため、エラーなし
        assert len(errors) == 0

        Path(f.name).unlink()


def test_ignore_comment():
    """pydantic-touchall: ignoreコメントでチェックをスキップするテスト"""
    code = '''
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

# ageが不足しているが、ignoreコメントでスキップ
user = User(  # pydantic-touchall: ignore
    name="Alice",
    email="alice@example.com",
)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # ignoreコメントがあるのでエラーなし
        assert len(errors) == 0

        Path(f.name).unlink()


def test_ignore_comment_short():
    """touchall: ignoreコメント（短縮形）でチェックをスキップするテスト"""
    code = '''
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

# ageが不足しているが、ignoreコメントでスキップ
user = User(  # touchall: ignore
    name="Alice",
    email="alice@example.com",
)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # ignoreコメントがあるのでエラーなし
        assert len(errors) == 0

        Path(f.name).unlink()


def test_ignore_field_comment():
    """pydantic-touchall: ignore-field でフィールドを個別に無視するテスト"""
    code = '''
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    name: str
    email: str
    age: int
    address: Optional[str] = None

# ageのみ無視、addressのエラーは検出される
user = User(  # pydantic-touchall: ignore-field age
    name="Alice",
    email="alice@example.com",
)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # ageは無視されるが、addressのエラーは検出される
        assert len(errors) == 1
        assert any("address" in err[2] for err in errors)
        assert not any("age" in err[2] for err in errors)

        Path(f.name).unlink()


def test_ignore_multiple_fields_comment():
    """pydantic-touchall: ignore-field で複数フィールドを無視するテスト"""
    code = '''
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    name: str
    email: str
    age: int
    address: Optional[str] = None
    nickname: str = "Anonymous"

# ageとaddressを無視
user = User(  # pydantic-touchall: ignore-field age, address
    name="Alice",
    email="alice@example.com",
)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # ageとaddressは無視されるが、nicknameのエラーは検出される
        assert len(errors) == 1
        assert any("nickname" in err[2] for err in errors)
        assert not any("age" in err[2] for err in errors)
        assert not any("address" in err[2] for err in errors)

        Path(f.name).unlink()


def test_ignore_comment_previous_line():
    """コメントが前の行にある場合のテスト"""
    code = '''
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

# pydantic-touchall: ignore
user = User(
    name="Alice",
    email="alice@example.com",
)
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()

        errors = check_file(f.name)

        # 前の行のignoreコメントでスキップされる
        assert len(errors) == 0

        Path(f.name).unlink()
