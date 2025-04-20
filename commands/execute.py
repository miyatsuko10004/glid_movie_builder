#!/usr/bin/env python
# -*- coding: utf-8 -*-

# システムパスの設定（先頭に配置）
import os
import sys
import multiprocessing
import platform

# Windows環境でmultiprocessingを正しく初期化
if sys.platform.startswith('win'):
    multiprocessing.freeze_support()

# プロジェクトルートディレクトリを取得してパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# その他のインポート
from moviepy.editor import *
import numpy as np
from dotenv import load_dotenv
from PIL import Image
import re
import cv2
from pathlib import Path
import time
import subprocess

# 色関連のユーティリティ関数
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

# 画像処理関連の関数
def crop_image_to_aspect_ratio(image_path, aspect_ratio_w, aspect_ratio_h, crop_position='center'):
    """画像を指定されたアスペクト比にトリミングする"""
    try:
        # パラメータチェック
        if aspect_ratio_w is None or aspect_ratio_h is None:
            print(f"エラー: crop_image_to_aspect_ratio - アスペクト比が指定されていません: {image_path}")
            return None
            
        if not os.path.exists(image_path):
            print(f"エラー: crop_image_to_aspect_ratio - 画像ファイルが存在しません: {image_path}")
            return None
            
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
    except Exception as e:
        import traceback
        print(f"エラー: 画像のトリミング中に例外が発生しました: {image_path}")
        print(f"パラメータ: aspect_ratio_w={aspect_ratio_w}, aspect_ratio_h={aspect_ratio_h}, crop_position={crop_position}")
        print(f"エラー詳細: {e}")
        traceback.print_exc()
        return None

# 画像ファイル名の生成関数
def get_image_filename(i):
    # プロジェクトルートディレクトリのパスを取得
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # すべての画像に対して2桁のゼロパディングを使用
    return os.path.join(root_dir, f"source/image_{i:02d}.jpeg")

# 画像処理用単純関数（並列処理用、ピクルング問題回避のため単純化）
def process_image_parallel(img_path, aspect_ratio_w, aspect_ratio_h, crop_position, image_height):
    """
    並列処理用の単純化された画像処理関数（MoviePyのクラスを含まないようにする）
    
    Args:
        img_path (str): 処理する画像のパス
        aspect_ratio_w (int): アスペクト比の幅
        aspect_ratio_h (int): アスペクト比の高さ
        crop_position (str): トリミング位置
        image_height (int): リサイズ後の画像の高さ
        
    Returns:
        str: 処理された画像の一時ファイルパス（エラー時はNone）
    """
    try:
        # パラメータのチェック
        if aspect_ratio_w is None or aspect_ratio_h is None:
            print(f"警告: アスペクト比が指定されていません: {img_path}")
            return None
        
        if image_height is None:
            print(f"警告: 画像の高さが指定されていません: {img_path}")
            return None
            
        # アスペクト比にトリミング
        temp_path = crop_image_to_aspect_ratio(img_path, aspect_ratio_w, aspect_ratio_h, crop_position)
        if temp_path is None:
            print(f"警告: 画像のトリミングに失敗しました: {img_path}")
            return None
            
        # ここではImageClipを作成せず、一時ファイルのパスのみを返す
        return temp_path
        
    except Exception as e:
        import traceback
        print(f"画像処理中にエラーが発生しました: {img_path}")
        print(f"パラメータ: aspect_ratio_w={aspect_ratio_w}, aspect_ratio_h={aspect_ratio_h}, crop_position={crop_position}, image_height={image_height}")
        print(f"エラー詳細: {e}")
        traceback.print_exc()
        return None

# 最適化ユーティリティをインポート
try:
    # デバッグ情報表示
    print("\n--- モジュールインポート情報 ---")
    print(f"システムパス: {sys.path}")
    
    # まずcommands内のoptimize_utilsを試す
    try:
        print("commands.optimize_utilsからのインポートを試みています...")
        from commands.optimize_utils import (
            get_system_info,
            get_optimal_worker_count,
            use_videotoolbox_encoding,
            optimize_ffmpeg_for_m2,
            process_images_in_parallel,
            print_system_report
        )
        print("commands.optimize_utilsからのインポートに成功しました")
        OPTIMIZE_AVAILABLE = True
        
        # 互換性のための関数定義
        def is_apple_silicon():
            system_info = get_system_info()
            return system_info.get('is_apple_silicon', False)
            
        def log_optimization_info():
            print_system_report()
            
        def parallel_process_images(image_paths, process_func, workers=None, **kwargs):
            return process_images_in_parallel(image_paths, process_func, *[], **kwargs)
            
        def create_optimized_ffmpeg_command(input_files, output_file, fps=30, resolution=None, high_quality=False):
            params = optimize_ffmpeg_for_m2(use_videotoolbox=USE_VIDEOTOOLBOX)
            cmd = ["ffmpeg", "-y"]
            cmd.extend(["-framerate", str(fps), "-i", input_files])
            
            # パラメータを追加
            for key, value in params.items():
                cmd.extend([f"-{key}", str(value)])
                
            # ビットレート
            cmd.extend(["-b:v", BITRATE])
            
            # 解像度設定
            if resolution:
                width, height = resolution
                cmd.extend(["-s", f"{width}x{height}"])
                
            cmd.append(output_file)
            return cmd
            
    except ImportError as e:
        # 次にutils内のoptimize_utilsを試す
        print(f"commands.optimize_utilsからのインポートに失敗: {e}")
        print("utils.optimize_utilsからのインポートを試みています...")
        
        try:
            from utils.optimize_utils import (
                is_apple_silicon, 
                use_videotoolbox_encoding, 
                get_optimal_worker_count,
                create_optimized_ffmpeg_command,
                parallel_process_images,
                log_optimization_info
            )
            print("utils.optimize_utilsからのインポートに成功しました")
            OPTIMIZE_AVAILABLE = True
        except ImportError as e2:
            print(f"utils.optimize_utilsからのインポートに失敗: {e2}")
            
            # 直接パスを指定して試す
            utils_path = os.path.join(project_root, "utils")
            if os.path.exists(utils_path):
                print(f"直接パスを指定してインポートを試みています: {utils_path}")
                sys.path.insert(0, utils_path)
                try:
                    from optimize_utils import (
                        is_apple_silicon, 
                        use_videotoolbox_encoding, 
                        get_optimal_worker_count,
                        create_optimized_ffmpeg_command,
                        parallel_process_images,
                        log_optimization_info
                    )
                    print("直接パスからのインポートに成功しました")
                    OPTIMIZE_AVAILABLE = True
                except ImportError as e3:
                    print(f"直接パスからのインポートに失敗: {e3}")
                    raise
            else:
                print(f"utilsディレクトリが見つかりません: {utils_path}")
                raise
        
except ImportError:
    # 最適化モジュールがない場合のフォールバック
    print("注意: 最適化モジュールが利用できません。標準モードで実行します。")
    print("内部でシンプルなフォールバック実装を使用します。")
    OPTIMIZE_AVAILABLE = True
    
    # シンプルなフォールバック実装
    def is_apple_silicon():
        try:
            if platform.system() != "Darwin":
                return False
            return platform.processor() == "arm" or "Apple" in subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode("utf-8").strip()
        except:
            return False
    
    def get_optimal_worker_count():
        import multiprocessing
        cores = multiprocessing.cpu_count()
        return max(1, min(6, int(cores * 0.75)))
    
    def use_videotoolbox_encoding():
        if not is_apple_silicon():
            return False
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], stdout=subprocess.PIPE, text=True, check=False)
            return "h264_videotoolbox" in result.stdout
        except:
            return False
    
    def parallel_process_images(image_paths, process_func, workers=None, **kwargs):
        if workers is None:
            workers = get_optimal_worker_count()
        
        if workers <= 1 or len(image_paths) <= 1:
            print(f"シングルスレッドで処理します")
            return [process_func(img_path, **kwargs) for img_path in image_paths]
        
        print(f"シンプルな並列処理: {workers}コアで実行")
        from concurrent.futures import ProcessPoolExecutor
        results = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(process_func, img_path, **kwargs): img_path for img_path in image_paths}
            for future in futures:
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"処理中にエラー: {e}")
                    results.append(None)
        return results
    
    def log_optimization_info():
        apple = "はい" if is_apple_silicon() else "いいえ"
        videotoolbox = "利用可能" if use_videotoolbox_encoding() else "利用不可"
        print("\n=== システム情報 ===")
        print(f"最適化: シンプルフォールバックモード")
        print(f"Apple Silicon: {apple}")
        print(f"VideoToolbox: {videotoolbox}")
        print(f"並列ワーカー数: {get_optimal_worker_count()}")
        print("===================\n")
    
    def create_optimized_ffmpeg_command(input_files, output_file, fps=30, resolution=None, high_quality=False):
        cmd = ["ffmpeg", "-y"]
        cmd.extend(["-framerate", str(fps), "-i", input_files])
        
        if use_videotoolbox_encoding():
            cmd.extend([
                "-c:v", "h264_videotoolbox",
                "-b:v", "5M",
                "-allow_sw", "1",
                "-profile:v", "high"
            ])
        else:
            cmd.extend([
                "-c:v", "libx264", 
                "-preset", "faster",
                "-crf", "23"
            ])
        
        # 解像度設定
        if resolution:
            width, height = resolution
            cmd.extend(["-s", f"{width}x{height}"])
        
        cmd.extend(["-pix_fmt", "yuv420p"])
        cmd.append(output_file)
        return cmd

# メイン処理関数を定義
def main():
    # .envファイルから環境変数を読み込む
    load_dotenv()

    # スクリプト開始時にシステム情報と最適化情報を表示
    print("==================== グリッド動画生成 ====================")
    print(f"実行日時: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    if OPTIMIZE_AVAILABLE:
        # 最適化情報を表示
        log_optimization_info()
        
        # Apple Silicon向け最適化の状態を表示
        if is_apple_silicon():
            print("🔥 Apple Silicon向け最適化を使用します")
            # use_videotoolbox_encoding()関数の呼び出し方法を修正
            try:
                vt_available = use_videotoolbox_encoding()
                print(f"⚡ ハードウェアエンコーディング: {'有効' if vt_available else '無効'}")
            except TypeError:
                # 互換性のためのワークアラウンド
                print("⚡ ハードウェアエンコーディング: 確認中")
        else:
            print("標準処理モードで実行します")
    else:
        print("標準処理モードで実行します（最適化モジュールが利用できません）")

    print("========================================================")

    # 環境変数から設定を読み込む
    global START_IMAGE_NUMBER, END_IMAGE_NUMBER, IMAGE_HEIGHT, GRID_ROWS, GRID_COLS
    global ANIMATION_DURATION, FPS, SLIDE_SPEED, PARALLEL_PROCESSING, USE_VIDEOTOOLBOX
    global MEMORY_BATCH_SIZE, FFMPEG_PRESET, BITRATE, ROOT_DIR, OUTPUT_FILENAME
    global FRAME_SIZE_PRESET, FRAME_WIDTH, FRAME_HEIGHT, ASPECT_RATIO_W, ASPECT_RATIO_H
    global CROP_POSITION, BACKGROUND_COLOR, GAP_HORIZONTAL, GAP_VERTICAL
    
    START_IMAGE_NUMBER = int(os.getenv('START_IMAGE_NUMBER', 1))
    END_IMAGE_NUMBER = int(os.getenv('END_IMAGE_NUMBER', 36))
    IMAGE_HEIGHT = int(os.getenv('IMAGE_HEIGHT', 100))
    GRID_ROWS = int(os.getenv('GRID_ROWS', 6))
    GRID_COLS = int(os.getenv('GRID_COLS', 6))
    ANIMATION_DURATION = int(os.getenv('ANIMATION_DURATION', 4))
    FPS = int(os.getenv('FPS', 30))
    # スライド速度の設定（1.0が通常速度、2.0は2倍速、0.5は半分速度）
    SLIDE_SPEED = float(os.getenv('SLIDE_SPEED', 1.0))

    # 最適化設定を読み込む
    PARALLEL_PROCESSING = os.getenv('PARALLEL_PROCESSING', 'true').lower() == 'true'
    USE_VIDEOTOOLBOX = os.getenv('USE_VIDEOTOOLBOX', 'true').lower() == 'true'
    MEMORY_BATCH_SIZE = int(os.getenv('MEMORY_BATCH_SIZE', 30))
    FFMPEG_PRESET = os.getenv('FFMPEG_PRESET', 'faster')
    BITRATE = os.getenv('BITRATE', '5M')

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

    # 並列処理を使用して画像を処理
    if OPTIMIZE_AVAILABLE and PARALLEL_PROCESSING and len(image_files_list) > 3:
        print(f"並列処理を使用して{len(image_files_list)}枚の画像を処理しています...")
        
        # 最適な並列ワーカー数を取得
        worker_count = get_optimal_worker_count() if OPTIMIZE_AVAILABLE else min(os.cpu_count() or 1, 4)
        print(f"並列処理ワーカー数: {worker_count}")
        
        # 画像を並列処理
        try:
            # 並列処理で画像ファイルのパスのみを取得
            temp_image_files = parallel_process_images(
                image_files_list, 
                process_image_parallel, 
                workers=worker_count, 
                aspect_ratio_w=ASPECT_RATIO_W, 
                aspect_ratio_h=ASPECT_RATIO_H, 
                crop_position=CROP_POSITION,
                image_height=IMAGE_HEIGHT
            )
            
            # 無効な結果をフィルタリング
            temp_image_files = [path for path in temp_image_files if path is not None]
            
            # 有効な結果があるか確認
            if not temp_image_files:
                raise ValueError("有効な処理結果がありません。通常処理にフォールバックします。")
                
            # ここでImageClipオブジェクトを作成（一括で処理）
            print(f"{len(temp_image_files)}枚の画像をクリップに変換しています...")
            images = [ImageClip(img_path).resize(height=IMAGE_HEIGHT) for img_path in temp_image_files]
            
        except Exception as e:
            print(f"並列処理中にエラーが発生しました。通常処理にフォールバックします: {e}")
            # 通常の逐次処理にフォールバック
            temp_image_files = []
            for img_path in image_files_list:
                temp_path = crop_image_to_aspect_ratio(img_path, ASPECT_RATIO_W, ASPECT_RATIO_H, CROP_POSITION)
                if temp_path:
                    temp_image_files.append(temp_path)
            
            # 有効な画像があるか確認
            if not temp_image_files:
                print("エラー: 有効な画像が処理できませんでした。処理を中止します。")
                sys.exit(1)
                
            # ImageClipを作成
            images = [ImageClip(img).resize(height=IMAGE_HEIGHT) for img in temp_image_files]
    else:
        # 通常の逐次処理
        print(f"{len(image_files_list)}枚の画像を処理しています...")
        # まず画像をトリミング
        temp_image_files = []
        for img_path in image_files_list:
            temp_path = crop_image_to_aspect_ratio(img_path, ASPECT_RATIO_W, ASPECT_RATIO_H, CROP_POSITION)
            if temp_path:
                temp_image_files.append(temp_path)
        
        # 有効な画像があるか確認
        if not temp_image_files:
            print("エラー: 有効な画像が処理できませんでした。処理を中止します。")
            sys.exit(1)
        
        # 次にImageClipを作成
        images = [ImageClip(img).resize(height=IMAGE_HEIGHT) for img in temp_image_files]

    # グリッド状に配置（ギャップを含む）
    if not images:
        print("エラー: 有効な画像が処理できませんでした。処理を中止します。")
        sys.exit(1)
        
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

    # 全てのクリップを合成（グリッド全体）
    grid_composite = CompositeVideoClip([background] + clips, size=(frame_w, frame_h))
    grid_composite = grid_composite.set_duration(ANIMATION_DURATION)

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

    # 最終的な背景を作成
    final_background = ColorClip(size=(final_width, final_height), color=BACKGROUND_COLOR)
    final_background = final_background.set_duration(ANIMATION_DURATION)

    # グリッドが右から左にスライドするアニメーション関数
    def make_slide_animation(t):
        # 右端から左端までスライド（フレーム幅分移動）
        progress = t / ANIMATION_DURATION * SLIDE_SPEED
        # 最初は画面右端から外にいて、最後は画面左端から外に出ていく
        x_pos = final_width - (final_width + frame_w) * progress
        # 垂直方向は中央に配置
        y_pos = (final_height - frame_h) // 2 if final_height > frame_h else 0
        return (x_pos, y_pos)

    # グリッドにアニメーションを適用
    sliding_grid = grid_composite.set_position(make_slide_animation)

    # 最終的な動画の作成
    final = CompositeVideoClip([final_background, sliding_grid], size=(final_width, final_height))

    # 最適化モジュールが利用可能で、VideoToolboxを使用する場合
    if OPTIMIZE_AVAILABLE and USE_VIDEOTOOLBOX:
        # VideoToolboxが利用可能かチェック
        vt_available = False
        try:
            vt_available = use_videotoolbox_encoding()
        except TypeError:
            # 古い関数シグネチャの場合は直接ffmpegで確認
            try:
                result = subprocess.run(["ffmpeg", "-encoders"], stdout=subprocess.PIPE, text=True, check=False)
                vt_available = "h264_videotoolbox" in result.stdout
            except:
                vt_available = False

        if vt_available:
            print("Apple Silicon向け最適化モードで動画をエンコードします...")
            
            # 一時ディレクトリに画像シーケンスとして保存
            temp_dir = os.path.join(os.path.dirname(OUTPUT_FILENAME), "temp_frames")
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # 画像シーケンスとして保存（write_framesの代わりにto_ImageClipで処理）
                print("フレームを画像シーケンスとして保存しています...")
                # 全フレームを生成してから保存する方法に変更
                for i, frame in enumerate(final.iter_frames(fps=FPS)):
                    frame_path = os.path.join(temp_dir, f"frame_{i:04d}.jpg")
                    # numpyのarrayをPIL Imageに変換して保存
                    Image.fromarray(frame).save(frame_path, quality=95)
                    # 進捗を表示
                    if i % 10 == 0:
                        print(f"フレーム保存進捗: {i}/{int(ANIMATION_DURATION * FPS)}")
                
                # 最適化されたFFmpegコマンドを生成
                resolution = (final_width, final_height)
                high_quality = FFMPEG_PRESET in ['slow', 'medium']
                
                # FFmpegで動画を生成
                ffmpeg_cmd = create_optimized_ffmpeg_command(
                    os.path.join(temp_dir, "frame_%04d.jpg"),
                    OUTPUT_FILENAME,
                    fps=FPS,
                    resolution=resolution,
                    high_quality=high_quality
                )
                
                print(f"FFmpegコマンドを実行: {' '.join(ffmpeg_cmd)}")
                subprocess.run(ffmpeg_cmd, check=True)
                print(f"動画の生成が完了しました: {OUTPUT_FILENAME}")
            except Exception as e:
                import traceback
                print(f"最適化エンコーディングに失敗しました。標準モードにフォールバックします: {e}")
                traceback.print_exc()
                final.write_videofile(OUTPUT_FILENAME, fps=FPS, codec='libx264')
            finally:
                # 一時ディレクトリの削除
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            # 標準のMoviePyエンコーディングを使用
            print("標準モードで動画をエンコードします（VideoToolboxは利用できません）...")
            final.write_videofile(OUTPUT_FILENAME, fps=FPS, codec='libx264')
    else:
        # 標準のMoviePyエンコーディングを使用
        print("標準モードで動画をエンコードします...")
        final.write_videofile(OUTPUT_FILENAME, fps=FPS, codec='libx264')

    # 一時ファイルを削除
    for temp_file in temp_image_files:
        try:
            os.remove(temp_file)
        except:
            pass
    
    print(f"動画の生成が完了しました: {OUTPUT_FILENAME}")

# Pythonスクリプトが直接実行された場合のみ実行
if __name__ == "__main__":
    main()

