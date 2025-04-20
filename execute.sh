#!/usr/bin/env bash

# execute.sh
#
# このスクリプトはcommands/execute.shを呼び出すためのラッパースクリプトです。

# デバッグ情報
echo "execute.sh: スクリプトを開始します..."
echo "現在のディレクトリ: $(pwd)"

# スクリプトが存在するディレクトリに移動
cd "$(dirname "$0")"
echo "移動先ディレクトリ: $(pwd)"

# commands/execute.shの存在確認
if [ -f "./commands/execute.sh" ]; then
    echo "commands/execute.shが見つかりました。実行します..."
    # commands/execute.shを呼び出す
    bash ./commands/execute.sh
else
    echo "エラー: commands/execute.shが見つかりません。"
    echo "ファイル一覧:"
    ls -la ./commands/
    exit 1
fi 