#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Apple Silicon (M1/M2/M3チップ)に最適化されたビデオ処理ユーティリティ

このモジュールは、Apple Siliconチップを搭載したMacで動作する場合に、
ビデオ処理パフォーマンスを最適化するための関数を提供します。

[互換性インターフェース]
commandsディレクトリにあるscript_utils.pyとutils/optimize_utils.pyの両方から
同じインターフェースでアクセスできるように設計されています。
"""

import os
import sys
import platform
import subprocess
import shutil
import tempfile
import multiprocessing
import psutil
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

# Metal機能をインポート (pyobjcがインストールされている場合)
METAL_AVAILABLE = False
try:
    import Metal
    import MetalPerformanceShaders
    METAL_AVAILABLE = True
except ImportError:
    pass

def is_apple_silicon():
    """
    実行環境がApple Silicon (M1/M2/M3)チップを搭載したMacかどうかを判定します。
    
    Returns:
        bool: Apple Siliconチップを搭載したMacの場合はTrue、それ以外の場合はFalse
    """
    if platform.system() != "Darwin":  # macOSかどうかを確認
        return False
    
    # macOSの場合、プロセッサ情報をチェック
    try:
        output = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode("utf-8").strip()
        return "Apple" in output
    except subprocess.SubprocessError:
        # コマンドが失敗した場合は別の方法を試みる
        return platform.processor() == "arm"

def get_system_info():
    """
    システム情報を取得します。
    
    Returns:
        dict: CPU、メモリ、GPUなどのシステム情報
    """
    memory = psutil.virtual_memory()
    info = {
        "cpu_count": multiprocessing.cpu_count(),
        "memory_total": memory.total / (1024 * 1024 * 1024),  # GB単位
        "available_memory_gb": memory.available / (1024 * 1024 * 1024),  # GB単位
        "metal_available": METAL_AVAILABLE,
    }
    
    # Appleシリコンチップかどうかを確認
    info["is_apple_silicon"] = is_apple_silicon()
    
    # 最適なワーカー数の計算
    if info["is_apple_silicon"]:
        info["optimal_workers"] = min(6, info["cpu_count"])
    else:
        info["optimal_workers"] = max(1, int(info["cpu_count"] * 0.75))
    
    return info

def get_optimal_worker_count():
    """
    M1/M2/M3チップに最適な並列ワーカー数を返します。
    
    Returns:
        int: 最適なワーカー数
    """
    # システム情報を取得
    system_info = get_system_info()
    return system_info["optimal_workers"]

def use_videotoolbox_encoding():
    """
    VideoToolboxエンコーディングが使用可能かどうかを判定します。
    
    Returns:
        bool: VideoToolboxエンコーディングが使用可能ならTrue、そうでなければFalse
    """
    # Apple Siliconかつffmpegでビデオツールボックスがサポートされていることを確認
    if not is_apple_silicon():
        return False
    
    try:
        # ffmpegコマンドが存在し、VideoToolboxをサポートしているか確認
        result = subprocess.run(
            ["ffmpeg", "-encoders"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return "h264_videotoolbox" in result.stdout
    except Exception:
        return False

def parallel_process_images(image_paths, process_func, workers=None, **kwargs):
    """
    画像を並列処理します。
    
    Args:
        image_paths (list): 処理する画像ファイルパスのリスト
        process_func (callable): 各画像に適用する処理関数
        workers (int, optional): 使用するワーカー数。Noneの場合は自動決定
        **kwargs: 処理関数に渡す追加の引数
    
    Returns:
        list: 処理結果のリスト
    """
    # ワーカー数が指定されていない場合は最適値を使用
    if workers is None:
        workers = get_optimal_worker_count()
    
    # 1つしか処理しない場合、または画像が少ない場合は並列化しない
    if workers == 1 or len(image_paths) <= 1:
        print(f"シングルスレッドで{len(image_paths)}枚の画像を処理します")
        return [process_func(img_path, **kwargs) for img_path in image_paths]
    
    # 並列処理の実行
    print(f"並列処理: {workers}コアで{len(image_paths)}枚の画像を処理します")
    results = []
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # 各画像の処理をSubmit
        future_to_path = {executor.submit(process_func, img_path, **kwargs): img_path 
                         for img_path in image_paths}
        
        # 結果を収集
        for future in future_to_path:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"画像処理中にエラーが発生しました: {future_to_path[future]} ({e})")
                results.append(None)
    
    return results

def optimize_ffmpeg_for_m2(use_videotoolbox=True):
    """
    M2チップ向けにFFmpegパラメータを最適化します。
    
    Args:
        use_videotoolbox (bool): VideoToolboxエンコーダーを使用するかどうか
        
    Returns:
        dict: 最適化されたFFmpegパラメータ
    """
    params = {}
    
    if use_videotoolbox and use_videotoolbox_encoding():
        params["c:v"] = "h264_videotoolbox"
    else:
        params["c:v"] = "libx264"
        params["preset"] = "faster"
    
    params["profile:v"] = "high"
    params["threads"] = str(get_optimal_worker_count())
    params["pix_fmt"] = "yuv420p"
    
    return params

def create_optimized_ffmpeg_command(input_files, output_file, fps=30, resolution=None, high_quality=False, extra_args=None):
    """
    システムに最適化されたFFmpegコマンドを生成します。
    
    Args:
        input_files (str): 入力ファイルのパターン（例: "frames/%04d.png"）
        output_file (str): 出力動画ファイルのパス
        fps (int): フレームレート
        resolution (tuple, optional): 出力解像度 (幅, 高さ)、Noneの場合は元のサイズを維持
        high_quality (bool): 高品質モードを使用するかどうか
        extra_args (list, optional): 追加のFFmpegパラメータ
    
    Returns:
        list: 最適化されたFFmpegコマンド（文字列のリスト）
    """
    cmd = ["ffmpeg", "-y"]
    
    # 入力ファイル設定
    cmd.extend(["-framerate", str(fps), "-i", input_files])
    
    # エンコーダー設定
    can_use_videotoolbox = use_videotoolbox_encoding()
    
    if can_use_videotoolbox:
        # VideoToolboxエンコーダー（Apple Silicon向け）
        cmd.extend([
            "-c:v", "h264_videotoolbox",
            "-b:v", "5M",  # ビットレート
            "-allow_sw", "1",  # ハードウェアエンコーディングが失敗した場合のソフトウェアフォールバック
            "-profile:v", "high"
        ])
    else:
        # 標準のlibx264エンコーダー
        preset = "slow" if high_quality else "faster"
        cmd.extend([
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", "18" if high_quality else "23"
        ])
    
    # 解像度設定
    if resolution:
        width, height = resolution
        cmd.extend(["-s", f"{width}x{height}"])
    
    # 共通設定
    cmd.extend(["-pix_fmt", "yuv420p"])
    
    # 追加の引数があれば追加
    if extra_args:
        cmd.extend(extra_args)
    
    # 出力ファイル
    cmd.append(output_file)
    
    return cmd

def print_system_report():
    """
    システム情報レポートを表示します。
    """
    info = get_system_info()
    
    print("\n=== システム情報レポート ===")
    print(f"CPU コア数: {info['cpu_count']}")
    print(f"メモリ: {info['memory_total']:.1f} GB (利用可能: {info['available_memory_gb']:.1f} GB)")
    print(f"Apple Silicon: {'はい' if info['is_apple_silicon'] else 'いいえ'}")
    print(f"Metal GPU: {'利用可能' if info['metal_available'] else '利用不可'}")
    print(f"VideoToolbox: {'利用可能' if use_videotoolbox_encoding() else '利用不可'}")
    print(f"最適なワーカー数: {info['optimal_workers']}")
    print("===========================\n")

def log_optimization_info():
    """
    現在のシステムの最適化情報をログに記録します。
    このメソッドはprint_system_reportのエイリアスです。
    """
    print_system_report()

# モジュールがインポートされた時に実行
if __name__ == "__main__":
    print_system_report() 