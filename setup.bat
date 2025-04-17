@echo off
setlocal

REM 仮想環境のディレクトリ名
set VENV_DIR=venv

REM 仮想環境が存在するか確認
if not exist %VENV_DIR% (
    echo 仮想環境を作成しています...
    python -m venv %VENV_DIR%
) else (
    echo 既存の仮想環境を使用します
)

REM 仮想環境をアクティベート
call %VENV_DIR%\Scripts\activate

REM 必要なパッケージをインストール
echo 必要なパッケージをインストールしています...
pip install -r requirements.txt

REM sourceディレクトリがなければ作成
if not exist source (
    echo sourceディレクトリを作成しています...
    mkdir source
    echo 画像ファイルは source ディレクトリに配置してください
)

REM outputディレクトリがなければ作成
if not exist output (
    echo outputディレクトリを作成しています...
    mkdir output
)

echo セットアップが完了しました！
echo 使用方法：
echo 1. %VENV_DIR%\Scripts\activate  # 仮想環境をアクティベート
echo 2. python execute.py            # プログラムを実行

endlocal 