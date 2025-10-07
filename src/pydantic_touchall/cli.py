"""コマンドラインインターフェース"""
import sys
import argparse
from pathlib import Path
from .checker import check_file


def main():
    """コマンドラインツールとして実行"""
    parser = argparse.ArgumentParser(
        description='PydanticのBaseModelフィールドチェックlinter'
    )
    parser.add_argument('files', nargs='+', help='チェックするPythonファイル')
    parser.add_argument(
        '--strict',
        action='store_true',
        help='オプショナルフィールドも警告対象にする'
    )

    args = parser.parse_args()

    total_errors = 0

    for filepath in args.files:
        errors = check_file(filepath, strict=args.strict)

        if errors:
            print(f"\n{filepath}:")
            for lineno, col, message in errors:
                print(f"  {lineno}:{col} - {message}")
                if message.startswith("Error:"):
                    total_errors += 1

    if total_errors > 0:
        print(f"\n合計 {total_errors} 個のエラーが見つかりました。")
        sys.exit(1)
    else:
        print("\n✓ 全てのチェックに合格しました。")
        sys.exit(0)


if __name__ == '__main__':
    main()
