# グリッド動画生成ツール 実装プロンプト

## 目的
グリッド動画生成ツールのパフォーマンスを劇的に向上させるため、Metal GPU活用と並列処理の最適化を実装する。

## 前提条件
- pyobjcがインストール済み
- CPU使用率99.9%の問題を解決する必要あり
- 処理時間を大幅に短縮する

## 実装方針

### 1. Metal GPU活用実装

```python
# commands/metal_utils.py (新規作成)

import Metal
import numpy as np
import cv2
import os
from typing import Tuple, Optional

class MetalImageProcessor:
    """Metal GPUを使用した画像処理クラス"""
    
    def __init__(self):
        self.device = Metal.MTLCreateSystemDefaultDevice()
        if self.device is None:
            raise RuntimeError("Metal GPUが利用できません")
        
        # デバイス情報ログ出力
        print(f"Metal GPU: {self.device.name()}")
        self.initialize_pipeline()
    
    def initialize_pipeline(self):
        """Metalパイプラインの初期化"""
        # シェーダ関数の設定
        # GPU処理用のパイプライン構築
        # ...
        
    def resize_image(self, img_data: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """
        画像をGPUを使ってリサイズする
        
        Args:
            img_data: 入力画像データ（numpy配列）
            target_size: 目標サイズ（幅, 高さ）
            
        Returns:
            リサイズされた画像データ（numpy配列）
        """
        # Metalバッファの作成
        # GPUメモリへのデータ転送
        # リサイズ処理の実行
        # 結果の取得
        # ...
        
    def process_batch(self, image_paths: list, target_size: Tuple[int, int]) -> list:
        """
        複数画像を一括処理する
        
        Args:
            image_paths: 処理する画像パスのリスト
            target_size: 目標サイズ（幅, 高さ）
            
        Returns:
            処理結果のリスト
        """
        results = []
        for path in image_paths:
            try:
                # OpenCVで画像を読み込み
                img = cv2.imread(path)
                if img is None:
                    continue
                    
                # GPUでリサイズ
                resized = self.resize_image(img, target_size)
                
                # 一時ファイルとして保存
                temp_path = f"temp_gpu_{os.path.basename(path)}"
                cv2.imwrite(temp_path, resized)
                results.append(temp_path)
            except Exception as e:
                print(f"画像処理エラー {path}: {e}")
                
        return results

# 使用例
metal_processor = MetalImageProcessor()
processed_images = metal_processor.process_batch(image_files, (target_width, target_height))
```

### 2. 最適化された並列処理フレームワーク

```python
# commands/parallel_framework.py (新規作成)

import os
import time
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Callable, List, Any, Dict, Union
import psutil

class OptimizedParallelProcessor:
    """最適化された並列処理フレームワーク"""
    
    def __init__(
        self, 
        worker_count: int = None, 
        use_threads_for_io: bool = True,
        memory_limit_percent: int = 85
    ):
        """
        初期化
        
        Args:
            worker_count: ワーカー数（未指定時は自動決定）
            use_threads_for_io: IO処理にスレッドを使用するか
            memory_limit_percent: メモリ使用制限（%）
        """
        self.cpu_count = os.cpu_count()
        self.worker_count = worker_count or max(8, min(16, self.cpu_count))
        self.use_threads_for_io = use_threads_for_io
        self.memory_limit_percent = memory_limit_percent
        
        print(f"並列処理フレームワーク初期化: {self.worker_count}ワーカー")
    
    def process_batch(
        self, 
        items: List[Any], 
        process_func: Callable,
        io_bound: bool = False,
        batch_size: int = 20,
        *args, **kwargs
    ) -> List[Any]:
        """
        バッチを並列処理する
        
        Args:
            items: 処理するアイテムのリスト
            process_func: 処理関数
            io_bound: IO主体の処理かどうか
            batch_size: バッチサイズ
            *args, **kwargs: 処理関数への追加引数
            
        Returns:
            処理結果のリスト
        """
        # メモリ監視
        def check_memory():
            if psutil.virtual_memory().percent > self.memory_limit_percent:
                import gc
                gc.collect()
                time.sleep(0.5)
        
        # 並列処理の実行
        results = []
        
        # 処理タイプに応じたExecutorを選択
        executor_class = ThreadPoolExecutor if io_bound or self.use_threads_for_io else ProcessPoolExecutor
        
        # バッチごとに処理
        for i in range(0, len(items), batch_size):
            check_memory()  # メモリチェック
            
            batch = items[i:i + batch_size]
            batch_results = []
            
            with executor_class(max_workers=self.worker_count) as executor:
                futures = [executor.submit(process_func, item, *args, **kwargs) for item in batch]
                for future in futures:
                    try:
                        result = future.result()
                        if result is not None:
                            batch_results.append(result)
                    except Exception as e:
                        print(f"並列処理エラー: {e}")
            
            results.extend(batch_results)
            
        return results

# 使用例
parallel_processor = OptimizedParallelProcessor()
processed_images = parallel_processor.process_batch(
    image_files, 
    process_image_function,
    io_bound=False, 
    batch_size=20,
    aspect_ratio_w=aspect_ratio_w,
    aspect_ratio_h=aspect_ratio_h
)
```

### 3. FFmpegパイプライン効率化

```python
# commands/ffmpeg_pipeline.py (新規作成)

import subprocess
import os
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import tempfile

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
            
        print(f"FFmpeg初期化: VideoToolbox={'有効' if self.videotoolbox_available else '無効'}")
    
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
        if self.videotoolbox_available:
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
            if self.videotoolbox_available:
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
                
                # 進捗表示
                if i % 10 == 0:
                    print(f"フレーム処理中: {i}/{frame_count}")
            
            # 入力を閉じて出力を待機
            process.stdin.close()
            process.wait()
            
            return process.returncode == 0
            
        except Exception as e:
            print(f"ストリーミング処理エラー: {e}")
            return False

# 使用例
pipeline = FFmpegPipeline(use_videotoolbox=True)
success = pipeline.stream_frames_to_video(
    generate_frame_function,
    "output/video.mp4",
    frame_count=120,
    fps=30,
    resolution=(1920, 1080)
)
```

## execute.py修正箇所

```python
# commands/execute.py の変更部分

from commands.metal_utils import MetalImageProcessor
from commands.parallel_framework import OptimizedParallelProcessor
from commands.ffmpeg_pipeline import FFmpegPipeline

def main():
    # 既存のコード...
    
    # Metal GPUプロセッサの初期化
    try:
        metal_processor = MetalImageProcessor()
        gpu_available = True
    except Exception as e:
        print(f"GPU処理の初期化に失敗: {e}")
        gpu_available = False
    
    # 並列処理フレームワークの初期化
    parallel_processor = OptimizedParallelProcessor(
        worker_count=int(os.getenv('THREAD_COUNT', 8))
    )
    
    # 画像処理
    if gpu_available and USE_GPU:
        # GPU処理
        print("GPUを使用して画像を処理しています...")
        target_sizes = [(int(image_width), int(IMAGE_HEIGHT)) for image_width in [...]]
        processed_images = metal_processor.process_batch(image_files_list, target_sizes)
    else:
        # CPU並列処理
        print("CPU並列処理で画像を処理しています...")
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
    
    # 動画生成（ストリーミング処理）
    ffmpeg_pipeline = FFmpegPipeline(use_videotoolbox=USE_VIDEOTOOLBOX)
    
    # フレーム生成関数の定義
    def generate_frame(frame_idx):
        # 時間点の計算
        t = frame_idx / (FPS * ANIMATION_DURATION)
        # スライド位置の計算
        position = make_slide_animation(t)
        # 合成処理でフレームを生成
        # ...
        return frame
    
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
        # 従来の処理...
    
    # 一時ファイルのクリーンアップ
    # ...
```

## .envファイル追加設定

```
# 最適化設定の追加
THREAD_COUNT=8
USE_GPU=true
GPU_MEMORY_LIMIT=2048
STREAM_PROCESSING=true
TEMP_DIR=/private/tmp/glid_processing
```

## デプロイ手順

1. 必要なパッケージのインストール確認
   ```bash
   pip install pyobjc numpy opencv-python psutil moviepy==1.0.3
   ```

2. 新規モジュールの配置
   - commands/metal_utils.py
   - commands/parallel_framework.py
   - commands/ffmpeg_pipeline.py

3. execute.pyの修正
   - 上記の変更を統合

4. .env設定の更新
   - 新しい最適化パラメータを追加

5. テスト実行
   ```bash
   ./execute.sh
   ```

## 成功指標

- CPU使用率: 60%以下
- GPU使用率: 50%以上
- 処理時間: 従来の1/5以下
- メモリ使用量: 2GB以下

## 注意事項

- Metal APIは macOS専用のため、他のプラットフォームでのフォールバック処理が必要
- 大量の画像処理時にもメモリ使用量を監視し、適宜GCを実行
- 処理速度と画質のバランスを考慮
- エラー処理を強化して、障害発生時に適切にフォールバック 