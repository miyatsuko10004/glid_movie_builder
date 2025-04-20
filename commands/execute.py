from moviepy.editor import *
import numpy as np
from dotenv import load_dotenv
import os
from PIL import Image
import re
import cv2
from pathlib import Path
import sys

# .envファイルから環境変数を読み込む
load_dotenv()

def color_name_to_rgb(color_name):
    """
    色名をRGB値に変換する
    
    Args:
        color_name (str): 色名（例：'white', 'black'など）
    
    Returns:
        tuple: RGB値のタプル（例：(255, 255, 255)）
    """
    color_map = {
        'white': (255, 255, 255),
        'black': (0, 0, 0),
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'blue': (0, 0, 255),
    }
    return color_map.get(color_name.lower(), (255, 255, 255))  # デフォルトは白

def parse_background_color(color_str):
    """
    背景色の文字列をRGB値に変換する
    
    Args:
        color_str (str): 色を表す文字列（例：'255,255,255'や'white'）
    
    Returns:
        tuple: RGB値のタプル
    """
    try:
        # カンマ区切りの数値の場合
        return tuple(map(int, color_str.split(',')))
    except ValueError:
        # 色名の場合
        return color_name_to_rgb(color_str)

def parse_color(color_str):
    """色文字列をRGB形式に変換する"""
    # カラーネームの場合はそのまま返す
    if color_str.lower() in ['white', 'black', 'red', 'green', 'blue', 'yellow', 'gray']:
        return color_str.lower()
    
    # HEX形式の場合（#FF0000）
    if color_str.startswith('#'):
        hex_color = color_str.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # RGB形式の場合（rgb(255,255,255)）
    rgb_match = re.match(r'rgb\((\d+),(\d+),(\d+)\)', color_str)
    if rgb_match:
        return tuple(map(int, rgb_match.groups()))
    
    # デフォルトは白
    return 'white'

# 環境変数から設定を読み込む
START_IMAGE_NUMBER = int(os.getenv('START_IMAGE_NUMBER', 1))
END_IMAGE_NUMBER = int(os.getenv('END_IMAGE_NUMBER', 36))
IMAGE_HEIGHT = int(os.getenv('IMAGE_HEIGHT', 100))
GRID_ROWS = int(os.getenv('GRID_ROWS', 6))
GRID_COLS = int(os.getenv('GRID_COLS', 6))
ANIMATION_DURATION = int(os.getenv('ANIMATION_DURATION', 4))
FPS = int(os.getenv('FPS', 30))
# スライド速度の設定（1.0が通常速度、2.0は2倍速、0.5は半分速度）
SLIDE_SPEED = float(os.getenv('SLIDE_SPEED', 1.0))

# プロジェクトルートディレクトリのパスを取得
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 出力ファイル名（プロジェクトルートからの相対パス）
output_path = os.getenv('OUTPUT_FILENAME', 'output/sliding_tiles.mp4')
OUTPUT_FILENAME = os.path.join(ROOT_DIR, output_path)

# 動画の枠サイズ設定
# プリセット値: 'HD'(1920x1080), 'HD_HALF'(1920x540) または 'AUTO'(グリッドサイズから自動計算)
FRAME_SIZE_PRESET = os.getenv('FRAME_SIZE_PRESET', 'AUTO')
# カスタムサイズを指定する場合（FRAME_SIZE_PRESET=CUSTOMの場合に使用）
FRAME_WIDTH = int(os.getenv('FRAME_WIDTH', 1920))
FRAME_HEIGHT = int(os.getenv('FRAME_HEIGHT', 1080))

ASPECT_RATIO_W = int(os.getenv('ASPECT_RATIO_W', 4))
ASPECT_RATIO_H = int(os.getenv('ASPECT_RATIO_H', 3))
CROP_POSITION = os.getenv('CROP_POSITION', 'center')
BACKGROUND_COLOR = parse_background_color(os.getenv('BACKGROUND_COLOR', '255,255,255'))
GAP_HORIZONTAL = int(os.getenv('GAP_HORIZONTAL', 0))
GAP_VERTICAL = int(os.getenv('GAP_VERTICAL', 0))

# outputディレクトリが存在しない場合は作成
output_dir = os.path.dirname(OUTPUT_FILENAME)
if output_dir:
    os.makedirs(output_dir, exist_ok=True)

def crop_image_to_aspect_ratio(image_path, aspect_ratio_w, aspect_ratio_h, crop_position='center'):
    """画像を指定されたアスペクト比にトリミングする"""
    with Image.open(image_path) as img:
        # 元の画像のサイズを取得
        width, height = img.size
        
        # 目標のアスペクト比
        target_ratio = aspect_ratio_w / aspect_ratio_h
        current_ratio = width / height
        
        if current_ratio > target_ratio:
            # 画像が横長すぎる場合、横をトリミング
            new_width = int(height * target_ratio)
            left_margin = int((width - new_width) / 2)
            if crop_position == 'left':
                left_margin = 0
            elif crop_position == 'right':
                left_margin = width - new_width
            
            img = img.crop((left_margin, 0, left_margin + new_width, height))
        else:
            # 画像が縦長すぎる場合、縦をトリミング
            new_height = int(width / target_ratio)
            top_margin = int((height - new_height) / 2)
            if crop_position == 'top':
                top_margin = 0
            elif crop_position == 'bottom':
                top_margin = height - new_height
            
            img = img.crop((0, top_margin, width, top_margin + new_height))
        
        # 一時ファイルとして保存
        temp_path = f"temp_{os.path.basename(image_path)}"
        img.save(temp_path)
        return temp_path

# 画像ファイル名の生成関数
def get_image_filename(i):
    # プロジェクトルートディレクトリのパスを取得
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # すべての画像に対して2桁のゼロパディングを使用
    return os.path.join(root_dir, f"source/image_{i:02d}.jpeg")

# 画像を読み込み、トリミングして一時ファイルとして保存
image_files_list = []
for i in range(START_IMAGE_NUMBER, END_IMAGE_NUMBER + 1):
    img_path = get_image_filename(i)
    if os.path.exists(img_path):
        image_files_list.append(img_path)
    else:
        print(f"警告: 画像ファイル {img_path} が見つかりません。スキップします。")

# 画像が一つも見つからない場合はエラーで終了
if not image_files_list:
    print("エラー: 有効な画像が見つかりません。処理を中止します。")
    sys.exit(1)

# 画像のトリミングと一時ファイルの作成
temp_image_files = [crop_image_to_aspect_ratio(img, ASPECT_RATIO_W, ASPECT_RATIO_H, CROP_POSITION) 
                   for img in image_files_list]

# トリミングした画像を読み込んでリサイズ
images = [ImageClip(img).resize(height=IMAGE_HEIGHT) for img in temp_image_files]

# グリッド状に配置（ギャップを含む）
tile_width = images[0].w
tile_height = images[0].h

# ギャップを含めたフレームサイズを計算
frame_w = (tile_width * GRID_COLS) + (GAP_HORIZONTAL * (GRID_COLS - 1))
frame_h = (tile_height * GRID_ROWS) + (GAP_VERTICAL * (GRID_ROWS - 1))

# 画像をグリッドに配置（ギャップ付き）
clips = []
for row in range(GRID_ROWS):
    row_clips = []
    for col in range(GRID_COLS):
        idx = row * GRID_COLS + col
        if idx < len(images):
            # 画像の位置を計算（ギャップを含む）
            x = col * (tile_width + GAP_HORIZONTAL)
            y = row * (tile_height + GAP_VERTICAL)
            clip = images[idx].set_position((x, y))
            row_clips.append(clip)
    if row_clips:
        clips.extend(row_clips)

# 背景クリップを作成
background = ColorClip(size=(frame_w, frame_h), color=BACKGROUND_COLOR)
background = background.set_duration(ANIMATION_DURATION)

# 全てのクリップを合成
composite = CompositeVideoClip([background] + clips, size=(frame_w, frame_h))

# 最終的な動画の枠サイズを設定
if FRAME_SIZE_PRESET == 'HD':
    final_width = 1920
    final_height = 1080
elif FRAME_SIZE_PRESET == 'HD_HALF':
    final_width = 1920
    final_height = 540
elif FRAME_SIZE_PRESET == 'CUSTOM':
    final_width = FRAME_WIDTH
    final_height = FRAME_HEIGHT
else:  # 'AUTO'
    final_width = frame_w
    final_height = frame_h

# スライド用のアニメーション（左→右）
# SLIDE_SPEEDを適用してスライド速度を調整
animated = composite.set_duration(ANIMATION_DURATION).set_position(
    lambda t: (-frame_w * t * SLIDE_SPEED / ANIMATION_DURATION, 0)
)

# 指定されたサイズの背景を作成（最終的な動画サイズ）
final_background = ColorClip(size=(final_width, final_height), color=BACKGROUND_COLOR)
final_background = final_background.set_duration(ANIMATION_DURATION)

# アニメーションを中央に配置するための計算
y_position = (final_height - frame_h) // 2 if final_height > frame_h else 0

# アニメーションのクリップを中央に配置
positioned_animation = animated.set_position((0, y_position))

# 最終的な動画の作成
final = CompositeVideoClip([final_background, positioned_animation], size=(final_width, final_height))
final.write_videofile(OUTPUT_FILENAME, fps=FPS, codec='libx264')

# 一時ファイルを削除
for temp_file in temp_image_files:
    try:
        os.remove(temp_file)
    except:
        pass

