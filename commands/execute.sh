#!/usr/bin/env bash

# execute.sh
#
# このスクリプトは execute.py を実行するためのシェルスクリプトです。
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

# source ディレクトリが存在するか確認
if [ -d "source" ]; then
    # source ディレクトリに画像が存在するか確認
    image_count=$(find source -name "image_*.jpeg" | wc -l)
    if [ "$image_count" -gt 0 ]; then
        echo "動画生成処理を開始します..."
        python commands/execute.py
    else
        echo "エラー: source ディレクトリに画像が見つかりません。"
        echo "先に画像を配置するか、./commands/convert.sh を実行して画像を準備してください。"
        exit 1
    fi
else
    echo "エラー: source ディレクトリが見つかりません。"
    echo "mkdir source コマンドでディレクトリを作成し、画像を配置してください。"
    exit 1
fi

# 仮想環境が有効化されていた場合は無効化
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

# スクリプト終了時にキーを押すと終了する（Windows用）
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "終了するには何かキーを押してください..."
    read -n1 -s
fi 