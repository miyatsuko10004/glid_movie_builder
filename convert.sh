#!/bin/bash

# convert.sh
#
# このスクリプトはcommands/convert.shを呼び出すためのラッパースクリプトです。

# デバッグ情報
echo "convert.sh: スクリプトを開始します..."
echo "現在のディレクトリ: $(pwd)"

# スクリプトが存在するディレクトリに移動
cd "$(dirname "$0")"
echo "移動先ディレクトリ: $(pwd)"

# commands/convert.shの存在確認
if [ -f "./commands/convert.sh" ]; then
    echo "commands/convert.shが見つかりました。実行します..."
    # commands/convert.shを呼び出す
    ./commands/convert.sh
else
    echo "エラー: commands/convert.shが見つかりません。"
    echo "ファイル一覧:"
    ls -la ./commands/
    exit 1
fi 