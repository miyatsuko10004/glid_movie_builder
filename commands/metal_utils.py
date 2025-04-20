#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
metal_utils.py

このスクリプトは、Metal GPUを使った画像処理機能を提供します。
Apple Silicon(M1/M2/M3)チップでのGPU処理を最適化し、
CPU使用率を軽減して処理速度を向上させます。
"""

import os
import numpy as np
import cv2
from typing import Tuple, List, Optional

# Metal関連のライブラリをインポート（pyobjcが必要）
METAL_AVAILABLE = False
try:
    import Metal
    import MetalPerformanceShaders as MPS
    METAL_AVAILABLE = True
except ImportError:
    pass

class MetalImageProcessor:
    """Metal GPUを使用した画像処理クラス"""
    
    def __init__(self):
        """
        Metal GPUプロセッサを初期化します。
        Metal APIが利用できない場合は例外を発生させます。
        """
        if not METAL_AVAILABLE:
            raise ImportError("Metal APIが利用できません。pyobjcパッケージが必要です。")
        
        self.device = Metal.MTLCreateSystemDefaultDevice()
        if self.device is None:
            raise RuntimeError("Metal GPUが利用できません")
        
        # デバイス情報ログ出力
        print(f"Metal GPU: {self.device.name()}")
        print(f"統合メモリ: {'有効' if self.device.hasUnifiedMemory() else '無効'}")
        print(f"低電力モード: {'有効' if self.device.isLowPower() else '無効'}")
        
        # コマンドキューの初期化
        self.command_queue = self.device.newCommandQueue()
        if self.command_queue is None:
            raise RuntimeError("Metal GPUコマンドキューを作成できません")
        
        # 画像処理フィルターの初期化
        self._initialize_filters()
    
    def _initialize_filters(self):
        """Metal画像処理フィルターを初期化します"""
        # リサイズフィルター
        self.resize_filter = MPS.MPSImageBilinearScale.alloc().initWithDevice_(self.device)
    
    def _create_texture(self, width, height, pixel_format=Metal.MTLPixelFormatRGBA8Unorm):
        """
        指定サイズのテクスチャを作成します
        
        Args:
            width (int): 幅
            height (int): 高さ
            pixel_format: ピクセルフォーマット
            
        Returns:
            Metal.MTLTexture: テクスチャ
        """
        descriptor = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
            pixel_format, width, height, False
        )
        descriptor.setUsage_(Metal.MTLTextureUsageShaderRead | Metal.MTLTextureUsageShaderWrite)
        texture = self.device.newTextureWithDescriptor_(descriptor)
        return texture
    
    def _load_image_to_texture(self, image_path):
        """
        画像ファイルをテクスチャにロードします
        
        Args:
            image_path (str): 画像ファイルパス
            
        Returns:
            tuple: (テクスチャ, 幅, 高さ)
        """
        # OpenCVで画像を読み込み
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"画像を読み込めません: {image_path}")
            
        # BGRからRGBAに変換
        img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        height, width = img_rgba.shape[:2]
        
        # テクスチャを作成
        texture = self._create_texture(width, height)
        
        # テクスチャリージョンを定義
        region = Metal.MTLRegionMake2D(0, 0, width, height)
        
        # データをテクスチャにコピー
        texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_(
            region, 0, img_rgba.tobytes(), width * 4
        )
        
        return texture, width, height
    
    def _texture_to_numpy(self, texture):
        """
        テクスチャをNumPy配列に変換します
        
        Args:
            texture (Metal.MTLTexture): 入力テクスチャ
            
        Returns:
            np.ndarray: NumPy配列
        """
        width = texture.width()
        height = texture.height()
        
        # テクスチャから画像データを取得
        region = Metal.MTLRegionMake2D(0, 0, width, height)
        bytes_per_row = width * 4  # RGBA
        data = bytearray(bytes_per_row * height)
        texture.getBytes_bytesPerRow_fromRegion_mipmapLevel_(data, bytes_per_row, region, 0)
        
        # バイト配列をNumPy配列に変換
        rgba_array = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 4)
        
        # RGBAからBGRに変換（OpenCV形式）
        bgr_array = cv2.cvtColor(rgba_array, cv2.COLOR_RGBA2BGR)
        
        return bgr_array
    
    def resize_image(self, img_path: str, target_size: Tuple[int, int]) -> np.ndarray:
        """
        画像をGPUを使ってリサイズします
        
        Args:
            img_path: 入力画像パス
            target_size: 目標サイズ（幅, 高さ）
            
        Returns:
            リサイズされた画像データ（numpy配列）
        """
        try:
            # 画像をテクスチャにロード
            source_texture, src_width, src_height = self._load_image_to_texture(img_path)
            
            # ターゲットサイズのテクスチャを作成
            target_width, target_height = target_size
            target_texture = self._create_texture(target_width, target_height)
            
            # コマンドバッファを作成
            command_buffer = self.command_queue.commandBuffer()
            
            # リサイズフィルターを適用
            self.resize_filter.encodeToCommandBuffer_sourceTexture_destinationTexture_(
                command_buffer, source_texture, target_texture
            )
            
            # コマンドバッファをコミットして実行
            command_buffer.commit()
            command_buffer.waitUntilCompleted()
            
            # テクスチャをNumPy配列に変換
            result = self._texture_to_numpy(target_texture)
            
            return result
        except Exception as e:
            print(f"GPU画像リサイズエラー: {e}")
            # フォールバック: CPU処理
            img = cv2.imread(img_path)
            if img is not None:
                return cv2.resize(img, target_size)
            return None
    
    def process_batch(self, image_paths: List[str], target_sizes: List[Tuple[int, int]]) -> List[str]:
        """
        複数画像を一括処理します
        
        Args:
            image_paths: 処理する画像パスのリスト
            target_sizes: 目標サイズのリスト（各要素は (幅, 高さ) のタプル）
            
        Returns:
            処理結果の一時ファイルパスのリスト
        """
        results = []
        
        for i, (img_path, target_size) in enumerate(zip(image_paths, target_sizes)):
            try:
                # Metal GPUでリサイズ
                resized_img = self.resize_image(img_path, target_size)
                
                if resized_img is None:
                    print(f"画像処理に失敗: {img_path}")
                    continue
                
                # 一時ファイルに保存
                temp_path = f"temp_gpu_{os.path.basename(img_path)}"
                cv2.imwrite(temp_path, resized_img)
                results.append(temp_path)
                
                # 処理進捗を表示
                if (i + 1) % 10 == 0 or i == len(image_paths) - 1:
                    print(f"GPU処理進捗: {i+1}/{len(image_paths)}")
                
            except Exception as e:
                print(f"GPU画像処理エラー {img_path}: {e}")
                # フォールバック処理
                try:
                    img = cv2.imread(img_path)
                    if img is not None:
                        resized = cv2.resize(img, target_size)
                        temp_path = f"temp_fallback_{os.path.basename(img_path)}"
                        cv2.imwrite(temp_path, resized)
                        results.append(temp_path)
                except Exception as inner_e:
                    print(f"フォールバック処理エラー: {inner_e}")
        
        return results 