#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
convert.py

このスクリプトは、アップロードディレクトリにある画像ファイルの名前を変更し、sourceディレクトリに移動する処理を行います。
画像ファイル名は「image_XX.jpeg」の形式で、sourceディレクトリに既に存在する画像の番号の続きになるように設定されます。

機能:
1. アップロードディレクトリが存在しない場合は作成
2. sourceディレクトリが存在しない場合は作成
3. sourceディレクトリの最後の画像番号を確認
4. アップロードディレクトリの画像を「image_XX.jpeg」の形式にリネームしてsourceディレクトリに移動
"""

import os
import shutil
import glob
import re
from PIL import Image
import sys

def ensure_directories():
    """
    必要なディレクトリが存在することを確認し、なければ作成します。
    
    Returns:
        tuple: (uploadディレクトリのパス, sourceディレクトリのパス)
    """
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload")
    source_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source")
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(source_dir, exist_ok=True)
    
    return upload_dir, source_dir

def get_last_image_number(source_dir):
    """
    sourceディレクトリ内の最後の画像番号を取得します。
    
    Args:
        source_dir (str): sourceディレクトリのパス
        
    Returns:
        int: 最後の画像番号。画像が存在しない場合は0を返します。
    """
    # sourceディレクトリ内の全ての画像ファイルを取得
    image_files = glob.glob(os.path.join(source_dir, "image_*.jpeg"))
    
    if not image_files:
        return 0
    
    # ファイル名から画像番号を抽出
    numbers = []
    for image_file in image_files:
        file_name = os.path.basename(image_file)
        match = re.search(r'image_(\d+)\.jpeg', file_name)
        if match:
            numbers.append(int(match.group(1)))
    
    # 番号の最大値を返す
    return max(numbers) if numbers else 0

def is_valid_image(file_path):
    """
    ファイルが有効な画像かどうかを確認します。
    
    Args:
        file_path (str): 画像ファイルのパス
        
    Returns:
        bool: 有効な画像であればTrue、そうでなければFalse
    """
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception as e:
        print(f"エラー: {file_path} は有効な画像ファイルではありません。({e})")
        return False

def convert_and_move_images(upload_dir, source_dir):
    """
    アップロードディレクトリ内の画像をリネームし、sourceディレクトリに移動します。
    
    Args:
        upload_dir (str): アップロードディレクトリのパス
        source_dir (str): sourceディレクトリのパス
        
    Returns:
        int: 処理した画像の数
    """
    # アップロードディレクトリ内の画像ファイルを取得
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.tiff']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(upload_dir, ext)))
    
    if not image_files:
        print(f"アップロードディレクトリ({upload_dir})に画像ファイルが見つかりませんでした。")
        return 0
    
    # sourceディレクトリの最後の画像番号を取得
    last_number = get_last_image_number(source_dir)
    
    # 処理した画像のカウンター
    processed_count = 0
    
    # 各画像ファイルを処理
    for image_file in image_files:
        # 有効な画像ファイルかどうか確認
        if not is_valid_image(image_file):
            continue
        
        # 新しい画像番号 (イテレーション毎に増加するのではなく、成功した画像の数に基づく)
        new_number = last_number + processed_count + 1
        
        # 新しいファイル名 (2桁の数字形式)
        if new_number < 10:
            new_filename = f"image_0{new_number}.jpeg"
        else:
            new_filename = f"image_{new_number}.jpeg"
        
        new_path = os.path.join(source_dir, new_filename)
        
        try:
            # 画像形式を変換してsourceディレクトリに保存
            with Image.open(image_file) as img:
                # RGBに変換（透明度チャンネルがある場合）
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                    img = background
                
                # JPEG形式で保存
                img.save(new_path, 'JPEG', quality=95)
            
            # 元のファイルを削除
            os.remove(image_file)
            
            processed_count += 1
            print(f"画像を変換しました: {os.path.basename(image_file)} -> {new_filename}")
            
        except Exception as e:
            print(f"エラー: 画像の処理中にエラーが発生しました: {image_file} ({e})")
    
    return processed_count

def main():
    """
    メイン処理を実行します。
    """
    print("画像変換処理を開始します...")
    
    # 必要なディレクトリを確認/作成
    upload_dir, source_dir = ensure_directories()
    
    # 画像の変換と移動を実行
    processed_count = convert_and_move_images(upload_dir, source_dir)
    
    if processed_count > 0:
        print(f"\n処理が完了しました。{processed_count}個の画像がsourceディレクトリに追加されました。")
    else:
        print("\n処理を完了しましたが、変換された画像はありませんでした。")
    
    print(f"アップロードディレクトリ: {upload_dir}")
    print(f"sourceディレクトリ: {source_dir}")

if __name__ == "__main__":
    main() 