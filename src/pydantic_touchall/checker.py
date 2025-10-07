import ast
import os
import sys
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FieldInfo:
    name: str
    has_default: bool
    is_optional: bool


class BaseModelFieldChecker(ast.NodeVisitor):
    """BaseModelの全フィールドが設定されているかチェックするlinter"""

    def __init__(self, base_path: str = "", source_lines: Optional[List[str]] = None):
        self.model_definitions: Dict[str, List[FieldInfo]] = {}
        self.errors: List[Tuple[int, int, str]] = []
        self.base_path = base_path or os.getcwd()
        self.processed_files: Set[str] = set()
        self.imported_models: Dict[str, str] = {}  # model_name -> module_path
        self.source_lines = source_lines or []

    def visit_Import(self, node: ast.Import):
        """import文を処理"""
        for alias in node.names:
            module_name = alias.name
            # import時のエイリアスがあればそれを使用、なければモジュール名をそのまま使用
            imported_as = alias.asname or module_name
            # モジュール全体のimportは対応しない（from X import Yのみ対応）
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """from X import Y文を処理"""
        if not node.module:
            return

        module_path = node.module
        for alias in node.names:
            if alias.name == '*':
                # from X import * は対応しない
                continue

            model_name = alias.asname or alias.name
            self.imported_models[model_name] = module_path

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """BaseModelを継承したクラスの定義を収集"""
        # BaseModelを継承しているか確認
        is_base_model = any(
            (isinstance(base, ast.Name) and base.id in ('BaseModel', 'Base')) or
            (isinstance(base, ast.Attribute) and base.attr in ('BaseModel', 'Base'))
            for base in node.bases
        )

        if is_base_model:
            fields = self._extract_fields(node)
            self.model_definitions[node.name] = fields

        self.generic_visit(node)

    def _extract_fields(self, class_node: ast.ClassDef) -> List[FieldInfo]:
        """クラスからフィールド情報を抽出"""
        fields = []

        for item in class_node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                has_default = item.value is not None

                # Optional[...]かどうかをチェック
                is_optional = self._is_optional_type(item.annotation)

                fields.append(FieldInfo(
                    name=field_name,
                    has_default=has_default,
                    is_optional=is_optional
                ))

        return fields

    def _is_optional_type(self, annotation) -> bool:
        """型アノテーションがOptionalかどうかをチェック"""
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return annotation.value.id == 'Optional'
            elif isinstance(annotation.value, ast.Attribute):
                return annotation.value.attr == 'Optional'
        return False

    def _resolve_module_path(self, module_name: str, current_file: str) -> Optional[str]:
        """モジュール名からファイルパスを解決"""
        # 相対importの場合（.で始まる）
        if module_name.startswith('.'):
            current_dir = os.path.dirname(current_file)
            # .の数だけ親ディレクトリに遡る
            level = len(module_name) - len(module_name.lstrip('.'))
            module_parts = module_name.lstrip('.').split('.')

            base_dir = current_dir
            for _ in range(level - 1):
                base_dir = os.path.dirname(base_dir)

            file_path = os.path.join(base_dir, *module_parts)
        else:
            # 絶対importの場合
            # まず現在のファイルからの相対パスで解決を試みる
            current_dir = os.path.dirname(current_file)
            module_parts = module_name.split('.')

            # プロジェクトルートを探す（pyproject.toml or setup.pyがあるディレクトリ）
            search_dir = current_dir
            project_root = None
            while search_dir != os.path.dirname(search_dir):  # ルートディレクトリに到達するまで
                if os.path.exists(os.path.join(search_dir, 'pyproject.toml')) or \
                   os.path.exists(os.path.join(search_dir, 'setup.py')):
                    project_root = search_dir
                    break
                search_dir = os.path.dirname(search_dir)

            if not project_root:
                # プロジェクトルートが見つからない場合は現在のディレクトリから探す
                project_root = current_dir

            file_path = os.path.join(project_root, *module_parts)

        # .py ファイルとして存在するか確認
        if os.path.exists(file_path + '.py'):
            return file_path + '.py'

        # __init__.py として存在するか確認
        init_path = os.path.join(file_path, '__init__.py')
        if os.path.exists(init_path):
            return init_path

        return None

    def _load_imported_model(self, model_name: str, current_file: str):
        """importされたモデルの定義を読み込む"""
        if model_name in self.model_definitions:
            # すでに定義済み
            return

        if model_name not in self.imported_models:
            # importされていない
            return

        module_path = self.imported_models[model_name]
        file_path = self._resolve_module_path(module_path, current_file)

        if not file_path or file_path in self.processed_files:
            return

        self.processed_files.add(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source, filename=file_path)

            # 新しいcheckerを作って、モデル定義のみを収集
            temp_checker = BaseModelFieldChecker(self.base_path)
            temp_checker.processed_files = self.processed_files  # 処理済みファイルを共有
            temp_checker.visit(tree)

            # モデル定義をマージ
            for name, fields in temp_checker.model_definitions.items():
                if name == model_name or name not in self.model_definitions:
                    self.model_definitions[name] = fields

        except (OSError, SyntaxError):
            # ファイルが読めない、またはパースエラーの場合は無視
            pass

    def visit_Call(self, node: ast.Call):
        """モデルのインスタンス化をチェック"""
        # クラス名を取得
        class_name = None
        if isinstance(node.func, ast.Name):
            class_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            class_name = node.func.attr

        if class_name:
            # importされたモデルの定義を読み込む
            if hasattr(self, 'current_file'):
                self._load_imported_model(class_name, self.current_file)

            # 定義済みのBaseModelクラスか確認
            if class_name in self.model_definitions:
                self._check_instantiation(node, class_name)

        self.generic_visit(node)

    def _check_ignore_comment(self, lineno: int) -> Tuple[bool, Set[str]]:
        """
        指定された行のignoreコメントをチェック

        Returns:
            (全体を無視するか, 無視するフィールド名のセット)
        """
        if not self.source_lines or lineno <= 0 or lineno > len(self.source_lines):
            return (False, set())

        # 該当する行とその前の行をチェック（コメントが前の行にある場合もある）
        lines_to_check = []
        if lineno > 0:
            lines_to_check.append(self.source_lines[lineno - 1])
        if lineno > 1:
            lines_to_check.append(self.source_lines[lineno - 2])

        for line in lines_to_check:
            # pydantic-touchall: ignore-field field1,field2 形式を先にチェック
            # (ignore より先にチェックしないと、ignore-field が ignore にマッチしてしまう)
            if '# pydantic-touchall: ignore-field' in line or '# touchall: ignore-field' in line:
                # コメント部分を抽出
                comment_part = line.split('#', 1)[1]
                if 'ignore-field' in comment_part:
                    # フィールド名を抽出
                    field_part = comment_part.split('ignore-field', 1)[1].strip()
                    ignored_fields = {f.strip() for f in field_part.split(',') if f.strip()}
                    return (False, ignored_fields)

            # pydantic-touchall: ignore コメントをチェック
            elif '# pydantic-touchall: ignore' in line or '# touchall: ignore' in line:
                return (True, set())

        return (False, set())

    def _check_instantiation(self, node: ast.Call, class_name: str):
        """インスタンス化時のフィールドチェック"""
        # ignoreコメントをチェック
        ignore_all, ignored_fields = self._check_ignore_comment(node.lineno)
        if ignore_all:
            return

        fields = self.model_definitions[class_name]

        # 必須フィールド（デフォルト値がなく、Optionalでもない）
        required_fields = {
            f.name for f in fields
            if not f.has_default and not f.is_optional
        }

        # 全フィールド
        all_fields = {f.name for f in fields}

        # 渡されている引数を収集
        provided_fields = set()
        has_kwargs = False

        # キーワード引数
        for keyword in node.keywords:
            if keyword.arg is None:  # **kwargs
                has_kwargs = True
            else:
                provided_fields.add(keyword.arg)

        # **kwargsがある場合はスキップ
        if has_kwargs:
            return

        # 必須フィールドのチェック（無視されたフィールドを除外）
        missing_required = (required_fields - provided_fields) - ignored_fields
        if missing_required:
            self.errors.append((
                node.lineno,
                node.col_offset,
                f"Error: {class_name}の必須フィールドが不足: {', '.join(sorted(missing_required))}"
            ))

        # 全フィールドのチェック（より厳密なチェック）
        missing_all = (all_fields - provided_fields) - ignored_fields
        if missing_all:
            optional_missing = [
                f.name for f in fields
                if f.name in missing_all and (f.has_default or f.is_optional)
            ]
            if optional_missing:
                self.errors.append((
                    node.lineno,
                    node.col_offset,
                    f"Error: {class_name}のオプションフィールドが未使用: {', '.join(sorted(optional_missing))}"
                ))

        # 未定義のフィールド
        unknown_fields = provided_fields - all_fields
        if unknown_fields:
            self.errors.append((
                node.lineno,
                node.col_offset,
                f"Error: {class_name}に存在しないフィールド: {', '.join(sorted(unknown_fields))}"
            ))


def check_file(filepath: str, strict: bool = True) -> List[Tuple[int, int, str]]:
    """
    ファイルをチェック

    Args:
        filepath: チェックするPythonファイル
        strict: Trueの場合、オプショナルフィールドも警告対象

    Returns:
        エラーと警告のリスト
    """
    # 絶対パスに変換
    filepath = os.path.abspath(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return [(e.lineno or 0, e.offset or 0, f"Syntax Error: {e.msg}")]

    # ソースコードを行ごとに分割
    source_lines = source.splitlines()

    checker = BaseModelFieldChecker(source_lines=source_lines)
    checker.current_file = filepath
    checker.processed_files.add(filepath)
    checker.visit(tree)

    return checker.errors
