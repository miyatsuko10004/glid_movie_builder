#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ram_disk_utils.py

このスクリプトはRAMディスクの作成と管理のためのユーティリティ関数を提供します。
一時ファイル処理を高速化し、ディスクI/Oのボトルネックを解消します。
"""

import os
import subprocess
import shutil
import tempfile
import platform
import psutil
import time
from typing import Optional

def setup_ram_disk(mount_point: Optional[str] = None, size: str = "6G") -> str:
    """
    RAMディスクをセットアップします。
    
    Args:
        mount_point (str): マウントポイント（Noneの場合は自動生成）
        size (str): サイズ（例: "6G"）
        
    Returns:
        str: RAMディスクのパス
    """
    # macOS以外のプラットフォームではRAMディスクをサポートしない
    if platform.system() != "Darwin":
        print("RAMディスクはmacOSでのみサポートされています。標準の一時ディレクトリを使用します。")
        return tempfile.gettempdir()
    
    # サイズをバイト数に変換
    size_value = int(size[:-1])
    size_unit = size[-1].upper()
    
    if size_unit == "G":
        size_bytes = size_value * 1024 * 2048  # セクタサイズは512バイト
    elif size_unit == "M":
        size_bytes = size_value * 2048
    else:
        print(f"サイズ単位が不明です: {size_unit}。デフォルトの2GBを使用します。")
        size_bytes = 2 * 1024 * 2048
    
    # マウントポイントの設定
    if mount_point is None:
        mount_point = "/tmp/glid_ramdisk"
    
    os.makedirs(mount_point, exist_ok=True)
    
    # 既存のRAMディスクをアンマウント（存在する場合）
    try:
        subprocess.run(["diskutil", "unmount", "force", mount_point], check=False, 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        pass
    
    # RAMディスクの作成とマウント
    try:
        print(f"{size}のRAMディスクを作成しています...")
        cmd = ["diskutil", "erasevolume", "HFS+", "GLID_RAMDISK", f"ram://{size_bytes}"]
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # マウントポイントの取得
        if result.returncode == 0:
            # 標準出力からマウントポイントを取得
            output = result.stdout.decode('utf-8')
            if "on " in output:
                mount_point = output.split("on ")[1].split(" ")[0]
            print(f"RAMディスクを作成しました: {mount_point}")
            return mount_point
    except Exception as e:
        print(f"RAMディスク作成エラー: {e}")
    
    print("RAMディスクの作成に失敗しました。標準の一時ディレクトリを使用します。")
    return tempfile.gettempdir()

def cleanup_ram_disk(mount_point: str) -> bool:
    """
    RAMディスクをクリーンアップします。
    
    Args:
        mount_point (str): RAMディスクのマウントポイント
        
    Returns:
        bool: 成功したかどうか
    """
    if platform.system() != "Darwin" or not mount_point:
        return False
    
    try:
        # 念のためファイルを削除
        for item in os.listdir(mount_point):
            item_path = os.path.join(mount_point, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"ファイル削除エラー: {e}")
        
        # RAMディスクをアンマウント
        subprocess.run(["diskutil", "unmount", "force", mount_point], check=False)
        print(f"RAMディスクをアンマウントしました: {mount_point}")
        return True
    except Exception as e:
        print(f"RAMディスクのクリーンアップに失敗しました: {e}")
        return False

def get_ramdisk_status() -> dict:
    """
    RAMディスクの状態情報を取得します。
    
    Returns:
        dict: RAMディスクのステータス情報
    """
    if platform.system() != "Darwin":
        return {"available": False, "reason": "macOSでのみサポート"}
    
    try:
        # diskutilでマウントされたボリュームの一覧を取得
        result = subprocess.run(["diskutil", "list"], stdout=subprocess.PIPE, text=True, check=False)
        
        # RAMディスクを検索
        ram_disks = []
        for line in result.stdout.splitlines():
            if "ram://" in line:
                parts = line.split()
                ram_disks.append({
                    "device": parts[0],
                    "size": parts[-2] + " " + parts[-1]
                })
        
        if ram_disks:
            return {
                "available": True,
                "count": len(ram_disks),
                "disks": ram_disks,
                "total_memory": psutil.virtual_memory().total / (1024**3),
                "available_memory": psutil.virtual_memory().available / (1024**3)
            }
        else:
            return {
                "available": False, 
                "reason": "RAMディスクがマウントされていません",
                "total_memory": psutil.virtual_memory().total / (1024**3),
                "available_memory": psutil.virtual_memory().available / (1024**3)
            }
    except Exception as e:
        return {"available": False, "reason": str(e)}

def get_optimal_ramdisk_size() -> str:
    """
    利用可能なメモリに基づいて最適なRAMディスクサイズを計算します。
    
    Returns:
        str: 推奨RAMディスクサイズ（例: "4G"）
    """
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024**3)
    available_gb = mem.available / (1024**3)
    
    # 利用可能なメモリの40%をRAMディスクに割り当て（上限4GB）
    optimal_size = min(4, available_gb * 0.4)
    
    # 1GB単位で切り捨て、最小は512MB
    if optimal_size < 0.5:
        return "512M"
    else:
        return f"{int(optimal_size)}G" 