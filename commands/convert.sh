#!/usr/bin/env bash

# convert.sh
#
# このスクリプトは convert.py を実行するためのシェルスクリプトです。
# 必要に応じて仮想環境を有効化し、Pythonスクリプトを実行します。

# スクリプトが存在するディレクトリに移動し、そこからプロジェクトルートへ
cd "$(dirname "$0")"
cd ..

# 仮想環境が存在するか確認
if [ -d "venv" ]; then
    echo "仮想環境を有効化しています..."
    
    # OSに応じて仮想環境を有効化
    if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # macOS または Linux
        source venv/bin/activate
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        source venv/Scripts/activate
    else
        echo "警告: 不明なOSタイプです。仮想環境の有効化に失敗した可能性があります。"
    fi
else
    echo "警告: 仮想環境が見つかりません。システムのPythonを使用します。"
fi

# convert.pyの実行
echo "画像変換処理を開始します..."
python commands/convert.py

# 仮想環境が有効化されていた場合は無効化
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

# スクリプト終了時にキーを押すと終了する（Windows用）
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "終了するには何かキーを押してください..."
    read -n1 -s
fi 