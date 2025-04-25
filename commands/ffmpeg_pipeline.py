#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ffmpeg_pipeline.py

このスクリプトは、効率的なFFmpegパイプラインを提供します。
Metal GPUのハードウェアエンコーディングを使用し、動画生成プロセスを最適化します。
"""

import subprocess
import os
import numpy as np
from typing import List, Tuple, Optional, Dict, Any, Callable
import tempfile
import platform
import time

class FFmpegPipeline:
    """効率的なFFmpegパイプライン"""
    
    def __init__(self, use_videotoolbox: bool = True):
        """
        初期化
        
        Args:
            use_videotoolbox: VideoToolboxを使用するか
        """
        self.use_videotoolbox = use_videotoolbox
        
        # VideoToolboxが利用可能か確認
        if self.use_videotoolbox:
            try:
                result = subprocess.run(["ffmpeg", "-encoders"], stdout=subprocess.PIPE, text=True, check=False)
                self.videotoolbox_available = "h264_videotoolbox" in result.stdout
            except:
                self.videotoolbox_available = False
        else:
            self.videotoolbox_available = False
        
        # プラットフォーム情報
        self.is_apple_silicon = self._check_apple_silicon()
        
        # 利用可能なハードウェアエンコーダーを取得
        self.available_encoders = self._get_available_encoders()
            
        print(f"FFmpeg初期化:")
        print(f"- VideoToolbox: {'有効' if self.videotoolbox_available else '無効'}")
        print(f"- Apple Silicon: {'有効' if self.is_apple_silicon else '無効'}")
        print(f"- 利用可能なHWエンコーダー: {', '.join(self.available_encoders) if self.available_encoders else 'なし'}")
    
    def _check_apple_silicon(self):
        """Apple Siliconチップかどうかを確認"""
        if platform.system() != "Darwin":
            return False
            
        try:
            cpu_info = os.popen('sysctl -n machdep.cpu.brand_string').read().strip()
            return "Apple" in cpu_info
        except:
            return False
    
    def _get_available_encoders(self):
        """利用可能なハードウェアエンコーダーを取得"""
        encoders = []
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], stdout=subprocess.PIPE, text=True, check=False)
            output = result.stdout
            
            # Apple Silicon向けのエンコーダーをチェック
            if "h264_videotoolbox" in output:
                encoders.append("h264_videotoolbox")
            if "hevc_videotoolbox" in output:
                encoders.append("hevc_videotoolbox")
                
            # NVIDIAのエンコーダーをチェック
            if "h264_nvenc" in output:
                encoders.append("h264_nvenc")
                
            # Intelのエンコーダーをチェック
            if "h264_qsv" in output:
                encoders.append("h264_qsv")
                
            # AMDのエンコーダーをチェック
            if "h264_amf" in output:
                encoders.append("h264_amf")
        except:
            pass
            
        return encoders
    
    def create_command(
        self,
        input_pattern: str,
        output_file: str,
        fps: int = 30,
        resolution: Optional[Tuple[int, int]] = None,
        bitrate: str = "5M",
        preset: str = "faster"
    ) -> List[str]:
        """
        最適化されたFFmpegコマンドを生成
        
        Args:
            input_pattern: 入力パターン（例: 'frames_%04d.jpg'）
            output_file: 出力ファイルパス
            fps: フレームレート
            resolution: 解像度 (幅, 高さ)
            bitrate: ビットレート
            preset: エンコードプリセット
            
        Returns:
            FFmpegコマンドのリスト
        """
        cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", input_pattern]
        
        # エンコーダ設定
        if self.videotoolbox_available and self.use_videotoolbox:
            cmd.extend([
                "-c:v", "h264_videotoolbox",
                "-b:v", bitrate,
                "-allow_sw", "1",
                "-realtime", "false",  # リアルタイム制約なし（高速化）
                "-profile:v", "high"
            ])
        else:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", "23",
                "-b:v", bitrate
            ])
        
        # 解像度設定
        if resolution:
            width, height = resolution
            cmd.extend(["-s", f"{width}x{height}"])
        
        cmd.extend(["-pix_fmt", "yuv420p", output_file])
        return cmd
    
    def execute_command(self, cmd: List[str], quiet: bool = False) -> bool:
        """
        FFmpegコマンドを実行
        
        Args:
            cmd: 実行するコマンド
            quiet: 出力を抑制するか
            
        Returns:
            成功したかどうか
        """
        try:
            start_time = time.time()
            
            if quiet:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            else:
                print(f"実行コマンド: {' '.join(cmd)}")
                result = subprocess.run(cmd, check=False)
            
            elapsed = time.time() - start_time
            success = result.returncode == 0
            
            if success:
                print(f"FFmpegコマンド実行成功: {elapsed:.1f}秒")
            else:
                print(f"FFmpegコマンド実行失敗: 終了コード {result.returncode}")
                
            return success
        except Exception as e:
            print(f"FFmpegコマンド実行エラー: {e}")
            return False
    
    def stream_frames_to_video(
        self, 
        frame_generator: Callable[[int], np.ndarray],
        output_file: str,
        frame_count: int,
        fps: int = 30,
        resolution: Tuple[int, int] = (1920, 1080)
    ) -> bool:
        """
        フレーム生成関数から直接動画を作成（一時ファイルなし）
        
        Args:
            frame_generator: フレーム生成関数（引数:フレーム番号、戻り値:numpy配列）
            output_file: 出力ファイルパス
            frame_count: 総フレーム数
            fps: フレームレート
            resolution: 解像度 (幅, 高さ)
            
        Returns:
            成功したかどうか
        """
        width, height = resolution
        
        try:
            # FFmpegコマンド構築
            cmd = [
                "ffmpeg", "-y",
                "-f", "rawvideo",
                "-vcodec", "rawvideo",
                "-s", f"{width}x{height}",
                "-pix_fmt", "rgb24",
                "-r", str(fps),
                "-i", "-"  # 標準入力から読み込み
            ]
            
            # エンコーダ設定
            if self.videotoolbox_available and self.use_videotoolbox:
                cmd.extend([
                    "-c:v", "h264_videotoolbox",
                    "-b:v", "5M",
                    "-allow_sw", "1"
                ])
            else:
                cmd.extend([
                    "-c:v", "libx264",
                    "-preset", "faster",
                    "-crf", "23"
                ])
                
            cmd.extend(["-pix_fmt", "yuv420p", output_file])
            
            print(f"ストリーミング処理を開始: {frame_count}フレーム, {fps}fps, {width}x{height}")
            
            # サブプロセス開始
            process = subprocess.Popen(
                cmd, 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                bufsize=10**8  # 大きなバッファ
            )
            
            # フレームをパイプで送信
            for i in range(frame_count):
                # フレーム生成
                frame = frame_generator(i)
                
                # RGB形式に変換
                if frame.shape[2] == 4:  # RGBA形式の場合
                    frame = frame[:, :, :3]
                
                # バイト配列に変換してプロセスに送信
                process.stdin.write(frame.tobytes())
                
                # 進捗表示（10フレームごと）
                if i % 10 == 0 or i == frame_count - 1:
                    progress = (i + 1) / frame_count * 100
                    print(f"フレーム処理中: {i+1}/{frame_count} ({progress:.1f}%)")
            
            # 入力を閉じて出力を待機
            process.stdin.close()
            process.wait()
            
            if process.returncode == 0:
                print(f"ストリーミング処理成功: {output_file}")
                return True
            else:
                print(f"ストリーミング処理エラー: 終了コード {process.returncode}")
                return False
            
        except Exception as e:
            print(f"ストリーミング処理エラー: {e}")
            return False
    
    def create_video_from_frames(
        self,
        frames_dir: str,
        output_file: str,
        frame_pattern: str = "frame_%04d.jpg",
        fps: int = 30,
        resolution: Optional[Tuple[int, int]] = None,
        bitrate: str = "5M"
    ) -> bool:
        """
        一連のフレーム画像から動画を作成
        
        Args:
            frames_dir: フレーム画像のディレクトリ
            output_file: 出力ファイルパス
            frame_pattern: フレームのパターン
            fps: フレームレート
            resolution: 解像度（オプション）
            bitrate: ビットレート
            
        Returns:
            成功したかどうか
        """
        # 入力パターンを作成
        input_pattern = os.path.join(frames_dir, frame_pattern)
        
        # 最適化されたコマンドを生成
        cmd = self.create_command(
            input_pattern=input_pattern,
            output_file=output_file,
            fps=fps,
            resolution=resolution,
            bitrate=bitrate
        )
        
        # コマンドを実行
        return self.execute_command(cmd) 