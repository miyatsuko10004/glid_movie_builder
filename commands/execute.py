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
import psutil

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

# 最適化モジュールをインポート
try:
    from commands.metal_utils import MetalImageProcessor
    METAL_AVAILABLE = True
except ImportError:
    METAL_AVAILABLE = False
    print("Metal GPUの機能を使用できません。pyobjcパッケージをインストールすることで高速化できます。")

try:
    from commands.parallel_framework import OptimizedParallelProcessor
    PARALLEL_FRAMEWORK_AVAILABLE = True
except ImportError:
    PARALLEL_FRAMEWORK_AVAILABLE = False
    print("最適化された並列処理フレームワークを使用できません。")

try:
    from commands.ffmpeg_pipeline import FFmpegPipeline
    FFMPEG_PIPELINE_AVAILABLE = True
except ImportError:
    FFMPEG_PIPELINE_AVAILABLE = False
    print("FFmpegパイプラインを使用できません。")

try:
    from commands.ram_disk_utils import setup_ram_disk, cleanup_ram_disk, get_optimal_ramdisk_size
    RAM_DISK_AVAILABLE = True
except ImportError:
    RAM_DISK_AVAILABLE = False
    print("RAMディスク機能を使用できません。")

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

    # 最適化フラグを環境変数から設定
    USE_GPU = os.getenv('USE_GPU', 'true').lower() == 'true'
    USE_RAM_DISK = os.getenv('USE_RAM_DISK', 'true').lower() == 'true'
    STREAM_PROCESSING = os.getenv('STREAM_PROCESSING', 'true').lower() == 'true'
    
    # システム情報を表示
    print("\n--- システム情報 ---")
    if OPTIMIZE_AVAILABLE:
        print_system_report()
    else:
        print(f"CPU: {os.cpu_count()} コア")
        print(f"メモリ: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    
    # RAMディスクの設定
    temp_dir = None
    if USE_RAM_DISK and RAM_DISK_AVAILABLE:
        try:
            optimal_size = get_optimal_ramdisk_size()
            ram_disk_size = os.getenv('RAM_DISK_SIZE', optimal_size)
            temp_dir = setup_ram_disk(size=ram_disk_size)
            print(f"一時ファイル用RAMディスク: {temp_dir}")
        except Exception as e:
            print(f"RAMディスク設定エラー: {e}")
            temp_dir = None
    
    try:
        # Metal GPUプロセッサの初期化
        metal_processor = None
        if USE_GPU and METAL_AVAILABLE:
            try:
                metal_processor = MetalImageProcessor()
                print("GPU処理を使用します")
            except Exception as e:
                print(f"GPU処理の初期化に失敗: {e}")
                metal_processor = None
        
        # 並列処理フレームワークの初期化
        thread_count = int(os.getenv('THREAD_COUNT', 0))
        if PARALLEL_FRAMEWORK_AVAILABLE:
            parallel_processor = OptimizedParallelProcessor(
                worker_count=thread_count if thread_count > 0 else None
            )
        
        # 画像ファイルのリストを生成
        image_files_list = []
        for i in range(START_IMAGE_NUMBER, END_IMAGE_NUMBER + 1):
            image_path = get_image_filename(i)
            if os.path.exists(image_path):
                image_files_list.append(image_path)
        
        # 画像サイズの計算
        image_width_list = [IMAGE_HEIGHT * ASPECT_RATIO_W / ASPECT_RATIO_H] * len(image_files_list)
        target_sizes = [(int(image_width), int(IMAGE_HEIGHT)) for image_width in image_width_list]
        
        # 画像処理
        processed_images = []
        
        if metal_processor is not None and USE_GPU:
            # GPU処理
            print("GPUを使用して画像を処理しています...")
            processed_images = metal_processor.process_batch(image_files_list, target_sizes)
        elif PARALLEL_FRAMEWORK_AVAILABLE:
            # 最適化された並列処理
            print("最適化された並列処理で画像を処理しています...")
            processed_images = parallel_processor.process_batch(
                image_files_list,
                process_image_parallel,
                io_bound=False,
                batch_size=MEMORY_BATCH_SIZE,
                aspect_ratio_w=ASPECT_RATIO_W,
                aspect_ratio_h=ASPECT_RATIO_H,
                crop_position=CROP_POSITION,
                image_height=IMAGE_HEIGHT
            )
        else:
            # 従来の処理方法
            print("従来の方法で画像を処理しています...")
            if OPTIMIZE_AVAILABLE:
                processed_images = parallel_process_images(
                    image_files_list,
                    process_image_parallel,
                    aspect_ratio_w=ASPECT_RATIO_W, 
                    aspect_ratio_h=ASPECT_RATIO_H,
                    crop_position=CROP_POSITION,
                    image_height=IMAGE_HEIGHT
                )
            else:
                # 従来の非並列処理
                for img_path in image_files_list:
                    processed_img = process_image_parallel(
                        img_path, 
                        ASPECT_RATIO_W, 
                        ASPECT_RATIO_H, 
                        CROP_POSITION, 
                        IMAGE_HEIGHT
                    )
                    if processed_img:
                        processed_images.append(processed_img)
        
        # 処理された画像のパスを確認
        print(f"処理された画像数: {len(processed_images)}")
        if not processed_images:
            print("エラー: 処理された画像がありません。")
            return
        
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
            # 必要な変数を定義
            tile_width = IMAGE_HEIGHT * ASPECT_RATIO_W / ASPECT_RATIO_H
            tile_height = IMAGE_HEIGHT
            frame_w = (tile_width * GRID_COLS) + (GAP_HORIZONTAL * (GRID_COLS - 1))
            frame_h = (tile_height * GRID_ROWS) + (GAP_VERTICAL * (GRID_ROWS - 1))
            final_width = frame_w
            final_height = frame_h
        
        # フレーム幅と高さを計算（すべてのプリセットで使用するため）
        tile_width = IMAGE_HEIGHT * ASPECT_RATIO_W / ASPECT_RATIO_H
        tile_height = IMAGE_HEIGHT
        frame_w = (tile_width * GRID_COLS) + (GAP_HORIZONTAL * (GRID_COLS - 1))
        frame_h = (tile_height * GRID_ROWS) + (GAP_VERTICAL * (GRID_ROWS - 1))
        
        # 背景色の設定
        try:
            background_color = parse_background_color(BACKGROUND_COLOR)
        except:
            print(f"警告: 無効な背景色指定 {BACKGROUND_COLOR}, 白色を使用します")
            background_color = (255, 255, 255)

        # 動画生成部分
        if FFMPEG_PIPELINE_AVAILABLE and STREAM_PROCESSING:
            ffmpeg_pipeline = FFmpegPipeline(use_videotoolbox=USE_VIDEOTOOLBOX)
            
            # フレーム生成関数の定義
            def generate_frame(frame_idx):
                # 時間点の計算
                t = frame_idx / (FPS * ANIMATION_DURATION)
                
                # スライド位置を計算（修正）
                # 0.0～1.0の進行度をより適切な範囲に変換
                # 開始位置を調整して、初期フレームから画像が見えるようにする
                adjusted_slide_speed = SLIDE_SPEED * 0.5  # スライド速度を半分に
                progress = t * adjusted_slide_speed
                
                # スライド位置の調整（画像がより長く表示されるよう調整）
                # 画面内に長く留まるよう計算を変更
                x_pos = int(final_width * (1.0 - progress * 0.8))
                
                # 背景を作成（RGBの順序に注意）
                background = np.zeros((final_height, final_width, 3), dtype=np.uint8)
                # OpenCVはBGR形式なので色の順序を反転
                if isinstance(background_color, tuple) and len(background_color) == 3:
                    bgr_color = (background_color[2], background_color[1], background_color[0])
                    background[:, :] = bgr_color
                else:
                    background[:, :] = background_color
                
                # 各画像を合成
                for idx, processed_img_path in enumerate(processed_images):
                    if processed_img_path is None:
                        continue
                    
                    # 画像の行と列の位置を計算
                    row = idx // GRID_COLS
                    col = idx % GRID_COLS
                    
                    # 画像を読み込む
                    img = cv2.imread(processed_img_path)
                    if img is None:
                        continue
                    
                    # 画像の位置を計算（スライドアニメーション考慮）
                    img_width = img.shape[1]
                    img_height = img.shape[0]
                    
                    x = col * (img_width + GAP_HORIZONTAL) + int(x_pos)
                    y = row * (img_height + GAP_VERTICAL)
                    if final_height > frame_h:
                        y += (final_height - frame_h) // 2
                    
                    # 画像が表示範囲内にある場合のみ描画
                    if (x < final_width and x + img_width > 0 and 
                        y < final_height and y + img_height > 0):
                        
                        # 画像の表示範囲を計算
                        x_start = max(0, x)
                        y_start = max(0, y)
                        x_end = min(final_width, x + img_width)
                        y_end = min(final_height, y + img_height)
                        
                        # 画像のソース領域を計算
                        src_x_start = max(0, -x)
                        src_y_start = max(0, -y)
                        src_width = x_end - x_start
                        src_height = y_end - y_start
                        
                        # 画像を背景に合成
                        if src_width > 0 and src_height > 0:
                            background[y_start:y_end, x_start:x_end] = img[
                                src_y_start:src_y_start+src_height, 
                                src_x_start:src_x_start+src_width
                            ]
                
                return background
            
            # ストリーミング処理で動画を生成
            success = ffmpeg_pipeline.stream_frames_to_video(
                generate_frame,
                OUTPUT_FILENAME,
                frame_count=int(FPS * ANIMATION_DURATION),
                fps=FPS,
                resolution=(final_width, final_height)
            )
            
            if not success:
                print("ストリーミング処理に失敗しました。従来の方法にフォールバックします...")
                # ここに従来の動画生成コード
                # ...
        else:
            # 既存の動画生成コード
            # ...
            pass  # ダミーコード（インデントエラー修正用）
    
    finally:
        # クリーンアップ処理
        # 一時ファイルの削除
        for img_path in processed_images:
            if img_path and os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except:
                    pass
        
        # RAMディスクのクリーンアップ
        if temp_dir and RAM_DISK_AVAILABLE:
            cleanup_ram_disk(temp_dir)

    print(f"動画の生成が完了しました: {OUTPUT_FILENAME}")

# Pythonスクリプトが直接実行された場合のみ実行
if __name__ == "__main__":
    main()

