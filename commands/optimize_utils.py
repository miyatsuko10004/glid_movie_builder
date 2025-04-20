#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
optimize_utils.py

このスクリプトは、Apple M2チップに最適化した動画処理のためのユーティリティ関数を提供します。
マルチコア処理、メモリ最適化、Metal GPU活用などの機能が含まれています。
"""

import os
import sys
import subprocess
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import numpy as np
import cv2
import psutil
from tqdm import tqdm
import time
import shutil
from pathlib import Path

# Metal機能をインポート (pyobjcがインストールされている場合)
METAL_AVAILABLE = False
try:
    import Metal
    import MetalPerformanceShaders
    METAL_AVAILABLE = True
except ImportError:
    pass

def get_system_info():
    """
    システム情報を取得します。
    
    Returns:
        dict: CPU、メモリ、GPUなどのシステム情報
    """
    info = {
        "cpu_count": multiprocessing.cpu_count(),
        "memory_total": psutil.virtual_memory().total / (1024 * 1024 * 1024),  # GB単位
        "metal_available": METAL_AVAILABLE,
    }
    
    # Appleシリコンチップかどうかを確認
    try:
        cpu_info = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
        info["is_apple_silicon"] = "Apple" in cpu_info
    except:
        info["is_apple_silicon"] = False
    
    return info

def get_optimal_worker_count():
    """
    M2チップに最適な並列ワーカー数を返します。
    
    Returns:
        int: 最適なワーカー数
    """
    # システム情報を取得
    system_info = get_system_info()
    total_cores = system_info["cpu_count"]
    
    # Apple Siliconの場合、パフォーマンスコアとエフィシエンシーコアを考慮
    if system_info["is_apple_silicon"]:
        # M2の場合は8コアで、4つがパフォーマンスコア、4つがエフィシエンシーコア
        # 最適値として6を返す（パフォーマンスコア4つ + エフィシエンシーコア2つ）
        # 残りのエフィシエンシーコアはシステム処理用に残す
        return min(6, total_cores)
    else:
        # 非Apple Siliconの場合は75%のコアを使用
        return max(1, int(total_cores * 0.75))

def setup_temp_directory():
    """
    最適な一時ディレクトリを設定します。
    
    Returns:
        str: 一時ディレクトリのパス
    """
    # 現在のディレクトリ内に一時ディレクトリを作成
    temp_dir = os.path.join(os.getcwd(), "temp_processing")
    os.makedirs(temp_dir, exist_ok=True)
    
    # 処理が早い一時ディレクトリを優先（macOSの場合）
    if sys.platform == "darwin":
        alt_temp = "/private/tmp/movie_processing"
        try:
            os.makedirs(alt_temp, exist_ok=True)
            temp_dir = alt_temp
        except:
            pass
    
    # 一時ディレクトリをクリア
    for item in os.listdir(temp_dir):
        item_path = os.path.join(temp_dir, item)
        try:
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            print(f"一時ファイルの削除に失敗: {e}")
            
    return temp_dir

def process_images_in_parallel(image_files, process_func, *args, **kwargs):
    """
    画像処理を並列で実行します。
    
    Args:
        image_files (list): 処理する画像ファイルのリスト
        process_func (function): 各画像に適用する処理関数
        *args, **kwargs: 処理関数に渡す追加の引数
        
    Returns:
        list: 処理結果のリスト
    """
    worker_count = get_optimal_worker_count()
    print(f"並列処理: {worker_count}コアで実行")
    
    results = []
    with tqdm(total=len(image_files), desc="画像処理") as pbar:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            # 進捗表示のためにfuturesを保持
            futures = []
            for img in image_files:
                future = executor.submit(process_func, img, *args, **kwargs)
                future.add_done_callback(lambda p: pbar.update(1))
                futures.append(future)
            
            # 結果を収集
            for future in futures:
                results.append(future.result())
    
    return results

def process_with_memory_optimization(items, batch_size, process_batch_func, *args, **kwargs):
    """
    メモリ使用量を最適化してバッチ処理を行います。
    
    Args:
        items (list): 処理する項目のリスト
        batch_size (int): バッチサイズ
        process_batch_func (function): バッチ処理関数
        *args, **kwargs: 処理関数に渡す追加の引数
        
    Returns:
        list: 処理結果のリスト
    """
    results = []
    total_items = len(items)
    
    # メモリ監視のためのしきい値
    memory_threshold = 85  # メモリ使用率が85%を超えたらGCを実行
    
    with tqdm(total=total_items, desc="バッチ処理") as pbar:
        for i in range(0, total_items, batch_size):
            # メモリ使用状況をチェック
            if psutil.virtual_memory().percent > memory_threshold:
                import gc
                gc.collect()
                print("メモリ最適化: ガベージコレクション実行")
                time.sleep(1)  # システムがメモリを解放する時間を与える
            
            end_idx = min(i + batch_size, total_items)
            batch = items[i:end_idx]
            
            # バッチを処理
            batch_results = process_batch_func(batch, *args, **kwargs)
            results.extend(batch_results)
            
            pbar.update(len(batch))
    
    return results

def use_videotoolbox_encoding(input_pattern, output_file, fps, width, height, bitrate="5M"):
    """
    Apple VideoToolboxを使用して高速エンコーディングを行います。
    
    Args:
        input_pattern (str): 入力画像のパターン (例: "temp/frame_%04d.jpg")
        output_file (str): 出力ファイルパス
        fps (int): フレームレート
        width (int): 出力動画の幅
        height (int): 出力動画の高さ
        bitrate (str): ビットレート (例: "5M")
        
    Returns:
        bool: 成功したかどうか
    """
    try:
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", input_pattern,
            "-c:v", "h264_videotoolbox",  # Apple Siliconハードウェアエンコーダー
            "-b:v", bitrate,
            "-s", f"{width}x{height}",
            "-tag:v", "avc1",
            "-pix_fmt", "yuv420p",
            output_file
        ]
        
        print("VideoToolboxエンコーディングを実行:")
        print(" ".join(cmd))
        
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print(f"VideoToolboxエンコーディングに失敗: {e}")
        return False

def check_metal_availability():
    """
    Metal GPUが利用可能かどうかを確認します。
    
    Returns:
        bool: Metal GPUが利用可能かどうか
    """
    if not METAL_AVAILABLE:
        return False
    
    try:
        # Metalデバイスを作成してチェック
        device = Metal.MTLCreateSystemDefaultDevice()
        return device is not None
    except:
        return False

def optimize_ffmpeg_for_m2(use_videotoolbox=True):
    """
    M2チップ向けにFFmpegパラメータを最適化します。
    
    Args:
        use_videotoolbox (bool): VideoToolboxエンコーダーを使用するかどうか
        
    Returns:
        dict: 最適化されたFFmpegパラメータ
    """
    params = {}
    
    if use_videotoolbox:
        params["c:v"] = "h264_videotoolbox"
    else:
        params["c:v"] = "libx264"
        params["preset"] = "faster"
    
    params["profile:v"] = "high"
    params["threads"] = str(get_optimal_worker_count())
    params["pix_fmt"] = "yuv420p"
    
    return params

def build_ffmpeg_command(input_path, output_path, params):
    """
    FFmpegコマンドを構築します。
    
    Args:
        input_path (str): 入力パス
        output_path (str): 出力パス
        params (dict): FFmpegパラメータ
        
    Returns:
        list: FFmpegコマンドのリスト
    """
    cmd = ["ffmpeg", "-y"]
    
    # 入力が画像シーケンスの場合
    if "%0" in input_path:
        rate_idx = input_path.find("%0")
        pattern = input_path[:rate_idx]
        if not os.path.exists(pattern):
            # 入力パターンをチェック
            cmd.extend(["-framerate", "30"])
    
    cmd.extend(["-i", input_path])
    
    # パラメータを追加
    for key, value in params.items():
        cmd.extend([f"-{key}", str(value)])
    
    cmd.append(output_path)
    return cmd

def cleanup_temp_files(temp_dir):
    """
    一時ファイルをクリーンアップします。
    
    Args:
        temp_dir (str): 一時ディレクトリのパス
    """
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"一時ディレクトリを削除: {temp_dir}")
    except Exception as e:
        print(f"一時ファイルのクリーンアップに失敗: {e}")

def print_system_report():
    """
    システム情報レポートを表示します。
    """
    info = get_system_info()
    
    print("\n=== システム情報レポート ===")
    print(f"CPU コア数: {info['cpu_count']}")
    print(f"メモリ: {info['memory_total']:.1f} GB")
    print(f"Apple Silicon: {'はい' if info.get('is_apple_silicon') else 'いいえ'}")
    print(f"Metal GPU: {'利用可能' if info['metal_available'] else '利用不可'}")
    print(f"最適なワーカー数: {get_optimal_worker_count()}")
    print("===========================\n")

# モジュールがインポートされた時に実行
if __name__ == "__main__":
    print_system_report() 