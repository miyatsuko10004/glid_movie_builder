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
mkdir -p source output upload
```

4. 環境変数設定ファイルの作成（任意）
```bash
cp .env.sample .env  # サンプルファイルからコピー
```
必要に応じて`.env`ファイルを編集して設定をカスタマイズできます。

## 使用方法

### 画像の準備

1. 画像ファイルを `source` ディレクトリに配置
   - 対応フォーマット: JPEG
   - ファイル名形式: `image_01.jpeg`, `image_02.jpeg`, ... （連番）

または

2. 画像変換ツールを使用して画像を準備（下記の「画像変換ツール」セクションを参照）

### 動画生成

```bash
./execute.sh
```

生成された動画は `output` ディレクトリに保存されます。

## 画像変換ツール

このプロジェクトには画像を簡単に追加するための変換ツールが含まれています。このツールを使用すると、さまざまな形式の画像ファイルを適切な形式（JPEG）に変換し、正しい命名規則で `source` ディレクトリに配置できます。

### 使用方法

1. 変換したい画像ファイルを `upload` ディレクトリに配置
   - 対応フォーマット: jpg/JPG, jpeg/JPEG, png/PNG, gif/GIF, bmp/BMP, tiff/TIFF
   - 小文字・大文字どちらの拡張子にも対応
   
2. 変換スクリプトを実行
```bash
./convert.sh
```

3. 変換処理が完了すると、画像は自動的に `source` ディレクトリに移動し、`image_XX.jpeg` の形式でリネームされます
   - 既に `source` ディレクトリに画像がある場合、新しい画像は既存の番号の続きから番号付けされます

### GUI アプリケーションとして実行する（macOS）

macOSでは、シェルスクリプトをGUIアプリケーションとして実行することもできます。

1. アプリケーションをビルドする
```bash
# Convert.appをビルド
osacompile -o apps/Convert.app Convert.applescript

# Execute.appをビルド
osacompile -o apps/Execute.app Execute.applescript
```

2. `apps` ディレクトリから、以下のアプリケーションをダブルクリックして実行できます：
   - `Convert.app`: 画像変換処理を実行
   - `Execute.app`: 動画生成を実行

これらのアプリケーションは、ターミナルウィンドウを自動的に開き、対応するスクリプトを実行します。

### 特徴

- 画像形式の自動変換（PNG, GIF, BMPなどをJPEGに変換）
- 小文字・大文字の拡張子に対応（.jpg/.JPGなど）
- 透明背景の画像は白色背景に変換
- 連番管理（既存の番号の続きから番号付け）
- 無効な画像ファイルの検出とスキップ

## 環境変数による設定

### .envファイルを使用した設定

プロジェクトルートに`.env`ファイルを作成することで、実行時の設定をカスタマイズできます。
このファイルに設定した環境変数は、スクリプト実行時に自動的に読み込まれます。

サンプル設定ファイル`.env.sample`が提供されており、これをコピーして独自の設定を行えます：

```bash
cp .env.sample .env
```

以下は.envファイルの例です：

```
# 画像の範囲設定
START_IMAGE_NUMBER=1
END_IMAGE_NUMBER=36

# グリッドの設定
GRID_ROWS=6
GRID_COLS=6
GAP_HORIZONTAL=0
GAP_VERTICAL=0

# 画像のサイズと形式
IMAGE_HEIGHT=100
ASPECT_RATIO_W=4
ASPECT_RATIO_H=3
CROP_POSITION=center

# 背景色
BACKGROUND_COLOR=255,255,255

# アニメーションの設定
ANIMATION_DURATION=4
FPS=30

# 出力設定
OUTPUT_FILENAME=output/sliding_tiles.mp4
```

### コマンドラインでの設定

一時的に設定を変更したい場合は、コマンドライン上で環境変数を指定することもできます：

```bash
# 背景色を黒に設定
BACKGROUND_COLOR=black ./execute.sh

# グリッドサイズを4x4に設定
GRID_ROWS=4 GRID_COLS=4 ./execute.sh

# アニメーション時間を6秒に設定
ANIMATION_DURATION=6 ./execute.sh

# 複数の設定を組み合わせる
BACKGROUND_COLOR=white GRID_ROWS=5 GRID_COLS=5 ANIMATION_DURATION=5 ./execute.sh
```

### 設定項目一覧

| 環境変数 | 説明 | デフォルト値 |
|----------|------|--------------|
| START_IMAGE_NUMBER | 開始画像番号 | 1 |
| END_IMAGE_NUMBER | 終了画像番号 | 36 |
| IMAGE_HEIGHT | 画像の高さ（ピクセル） | 100 |
| GRID_ROWS | グリッドの行数 | 6 |
| GRID_COLS | グリッドの列数 | 6 |
| ANIMATION_DURATION | アニメーション時間（秒） | 4 |
| FPS | フレームレート | 30 |
| OUTPUT_FILENAME | 出力ファイル名 | output/sliding_tiles.mp4 |
| ASPECT_RATIO_W | アスペクト比（幅） | 4 |
| ASPECT_RATIO_H | アスペクト比（高さ） | 3 |
| CROP_POSITION | クロップ位置（center/left/right/top/bottom） | center |
| BACKGROUND_COLOR | 背景色（white/black/red/green/blue または R,G,B形式） | 255,255,255 |
| GAP_HORIZONTAL | 画像間の水平方向の間隔（ピクセル） | 0 |
| GAP_VERTICAL | 画像間の垂直方向の間隔（ピクセル） | 0 |

## ディレクトリ構成

```
prfile_movie_source/
├── README.md
├── .env.sample         # 環境変数設定ファイルのサンプル
├── .env                # 環境変数設定ファイル（gitignore対象）
├── convert.sh         # 画像変換スクリプトのラッパー
├── execute.sh         # 動画生成スクリプトのラッパー
├── Convert.applescript # macOS用画像変換アプリスクリプト
├── Execute.applescript # macOS用動画生成アプリスクリプト
├── commands/          # コマンドスクリプトディレクトリ
│   ├── convert.py     # 画像変換スクリプト
│   ├── convert.sh     # 画像変換シェルスクリプト
│   ├── execute.py     # 動画生成スクリプト
│   └── execute.sh     # 動画生成シェルスクリプト
├── apps/              # macOS用アプリケーションディレクトリ (生成後)
│   ├── Convert.app    # 画像変換アプリケーション
│   └── Execute.app    # 動画生成アプリケーション
├── requirements.txt   # 依存パッケージリスト
├── output/            # 出力動画ディレクトリ
│   └── sliding_tiles.mp4  # 生成される動画ファイル
├── source/            # 入力画像ディレクトリ
│   ├── image_01.jpeg
│   ├── image_02.jpeg
│   └── ...
└── upload/            # 画像アップロードディレクトリ
```

## 注意事項

- 画像ファイルは連番で命名してください（image_01.jpeg, image_02.jpeg, ...）
- 画像は自動的に指定されたアスペクト比（デフォルト4:3）にクロップされます
- 一時ファイルは処理後に自動的に削除されます
- 変換処理後、アップロードディレクトリの画像は削除されます
