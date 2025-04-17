# グリッド動画生成ツール

このツールは、複数の画像をグリッド状に配置し、横スライドするアニメーション動画を生成します。

## 必要な環境

- Python 3.11以上
- pip（Pythonパッケージマネージャー）

## 注意事項

このツールは特定のバージョンのパッケージに依存しています：
- moviepy 1.0.3（新しいバージョンでは動作しません）

## セットアップ手順

### 自動セットアップ（推奨）

#### macOS/Linux
```bash
chmod +x setup.sh  # 実行権限を付与
./setup.sh
```

#### Windows
```
setup.bat
```

### 手動セットアップ

1. 仮想環境の作成（推奨）
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows
```

2. 必要なパッケージのインストール
```bash
pip install -r requirements.txt
# または
pip install opencv-python moviepy==1.0.3 numpy python-dotenv Pillow
```

3. 必要なディレクトリの作成
```bash
mkdir -p source output
```

## 使用方法

1. 画像ファイルを `source` ディレクトリに配置
   - 対応フォーマット: JPEG
   - ファイル名形式: `image_01.jpeg`, `image_02.jpeg`, ... （連番）

2. プログラムの実行
```bash
python execute.py
```

生成された動画は `output` ディレクトリに保存されます。

## 環境変数による設定

以下の環境変数を使用して、動画の生成設定をカスタマイズできます：

| 環境変数 | 説明 | デフォルト値 |
|----------|------|--------------|
| START_IMAGE_NUMBER | 開始画像番号 | 1 |
| END_IMAGE_NUMBER | 終了画像番号 | 36 |
| IMAGE_HEIGHT | 画像の高さ（ピクセル） | 100 |
| GRID_ROWS | グリッドの行数 | 6 |
| GRID_COLS | グリッドの列数 | 6 |
| ANIMATION_DURATION | アニメーション時間（秒） | 4 |
| FPS | フレームレート | 30 |
| OUTPUT_FILENAME | 出力ファイル名 | sliding_tiles.mp4 |
| ASPECT_RATIO_W | アスペクト比（幅） | 4 |
| ASPECT_RATIO_H | アスペクト比（高さ） | 3 |
| CROP_POSITION | クロップ位置（center/left/right/top/bottom） | center |
| BACKGROUND_COLOR | 背景色（white/black/red/green/blue または R,G,B形式） | 255,255,255 |
| GAP_HORIZONTAL | 画像間の水平方向の間隔（ピクセル） | 0 |
| GAP_VERTICAL | 画像間の垂直方向の間隔（ピクセル） | 0 |

### 使用例

```bash
# 背景色を黒に設定
BACKGROUND_COLOR=black python execute.py

# グリッドサイズを4x4に設定
GRID_ROWS=4 GRID_COLS=4 python execute.py

# アニメーション時間を6秒に設定
ANIMATION_DURATION=6 python execute.py

# 複数の設定を組み合わせる
BACKGROUND_COLOR=white GRID_ROWS=5 GRID_COLS=5 ANIMATION_DURATION=5 python execute.py
```

## ディレクトリ構成

```
prfile_movie_source/
├── README.md
├── execute.py          # メインスクリプト
├── sliding_tiles.mp4   # 生成される動画ファイル
└── source/            # 入力画像ディレクトリ
    ├── image_01.jpeg
    ├── image_02.jpeg
    └── ...
```

## 注意事項

- 画像ファイルは連番で命名してください（image_01.jpeg, image_02.jpeg, ...）
- 画像は自動的に指定されたアスペクト比（デフォルト4:3）にクロップされます
- 一時ファイルは処理後に自動的に削除されます 
