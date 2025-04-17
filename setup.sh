#!/bin/bash

# 仮想環境のディレクトリ名
VENV_DIR="venv"

# 仮想環境が存在するか確認
if [ ! -d "$VENV_DIR" ]; then
    echo "仮想環境を作成しています..."
    python3 -m venv $VENV_DIR
else
    echo "既存の仮想環境を使用します"
fi

# 仮想環境をアクティベート
source $VENV_DIR/bin/activate

# 必要なパッケージをインストール
echo "必要なパッケージをインストールしています..."
pip install opencv-python moviepy numpy python-dotenv Pillow

# sourceディレクトリがなければ作成
if [ ! -d "source" ]; then
    echo "sourceディレクトリを作成しています..."
    mkdir source
    echo "画像ファイルは source ディレクトリに配置してください"
fi

echo "セットアップが完了しました！"
echo "使用方法："
echo "1. source $VENV_DIR/bin/activate  # 仮想環境をアクティベート"
echo "2. python execute.py              # プログラムを実行" 