# グリッド動画生成ツール GPU最適化プロンプト

## 目的
Metal GPUを最大限に活用してグリッド動画生成ツールのパフォーマンスを向上させる。

## 現状の課題
- pyobjcのインストールにより、Metal APIは利用可能になったが、実際の処理でGPUが活用されていない
- GPU使用率が0%と表示されており、処理がすべてCPUに依存している
- 画像処理とエンコーディングに適したGPUリソースが未活用のまま
- Metal APIの実装が不完全または効率的でない

## GPU最適化の方針

### 1. Metal API活用のための基本実装

```python
# commands/metal_core.py (新規作成)

import Metal
import MetalPerformanceShaders as MPS
import numpy as np
import cv2
import time
from typing import Tuple, List, Optional

class MetalCore:
    """Metal GPUを扱うためのコアクラス"""
    
    def __init__(self):
        """Metal GPUデバイスを初期化"""
        self.device = Metal.MTLCreateSystemDefaultDevice()
        if self.device is None:
            raise RuntimeError("Metal GPUデバイスが利用できません")
            
        self.command_queue = self.device.newCommandQueue()
        if self.command_queue is None:
            raise RuntimeError("Metal GPUコマンドキューを作成できません")
            
        # デバイス情報を出力
        print(f"Metal GPU: {self.device.name()}")
        print(f"統合メモリ: {'有効' if self.device.hasUnifiedMemory() else '無効'}")
        print(f"最大バッファサイズ: {self.device.maxBufferLength() / 1024 / 1024:.1f} MB")
        
        self.initialized = True
    
    def create_buffer(self, data):
        """
        NumPy配列からMetalバッファを作成
        
        Args:
            data (np.ndarray): 入力データ
            
        Returns:
            Metal.MTLBuffer: Metalバッファ
        """
        data_size = data.nbytes
        buffer = self.device.newBufferWithBytes_length_options_(
            data.tobytes(), data_size, Metal.MTLResourceStorageModeShared
        )
        return buffer
    
    def create_texture(self, width, height, pixel_format=Metal.MTLPixelFormatRGBA8Unorm):
        """
        指定サイズのテクスチャを作成
        
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
    
    def load_image_to_texture(self, image_path):
        """
        画像ファイルをテクスチャにロード
        
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
        texture = self.create_texture(width, height)
        
        # テクスチャリージョンを定義
        region = Metal.MTLRegionMake2D(0, 0, width, height)
        
        # データをテクスチャにコピー
        texture.replaceRegion_mipmapLevel_withBytes_bytesPerRow_(
            region, 0, img_rgba.tobytes(), width * 4
        )
        
        return texture, width, height
    
    def texture_to_numpy(self, texture):
        """
        テクスチャをNumPy配列に変換
        
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
```

### 2. 画像処理用のGPUアクセラレーション

```python
# commands/metal_image_processor.py (新規作成)

import Metal
import MetalPerformanceShaders as MPS
import numpy as np
import cv2
import os
from commands.metal_core import MetalCore
from typing import Tuple, List, Dict, Any, Optional

class MetalImageProcessor:
    """Metal GPUを使用した画像処理クラス"""
    
    def __init__(self):
        """初期化"""
        self.core = MetalCore()
        self.kernels = {}
        self._load_kernels()
        
        print("Metal画像処理エンジンを初期化しました")
    
    def _load_kernels(self):
        """シェーダーカーネルをロード"""
        # 標準ライブラリ機能を使用
        self.resize_scale_filter = MPS.MPSImageBilinearScale.alloc().initWithDevice_(self.core.device)
    
    def resize_image(self, input_path: str, target_size: Tuple[int, int]) -> np.ndarray:
        """
        画像をリサイズ
        
        Args:
            input_path (str): 入力画像パス
            target_size (tuple): 目標サイズ (幅, 高さ)
            
        Returns:
            np.ndarray: リサイズされた画像
        """
        # 画像をロード
        source_texture, src_width, src_height = self.core.load_image_to_texture(input_path)
        
        # ターゲットサイズのテクスチャを作成
        target_width, target_height = target_size
        target_texture = self.core.create_texture(target_width, target_height)
        
        # コマンドバッファを作成
        command_buffer = self.core.command_queue.commandBuffer()
        
        # リサイズフィルターを適用
        self.resize_scale_filter.encodeToCommandBuffer_sourceTexture_destinationTexture_(
            command_buffer, source_texture, target_texture
        )
        
        # コマンドバッファをコミットして実行
        command_buffer.commit()
        command_buffer.waitUntilCompleted()
        
        # テクスチャをNumPy配列に変換
        result = self.core.texture_to_numpy(target_texture)
        
        return result
    
    def process_batch(self, image_paths: List[str], target_sizes: List[Tuple[int, int]]) -> List[str]:
        """
        複数画像をバッチ処理
        
        Args:
            image_paths (list): 画像パスのリスト
            target_sizes (list): ターゲットサイズのリスト (各要素は (幅, 高さ) のタプル)
            
        Returns:
            list: 処理された画像の一時ファイルパスのリスト
        """
        results = []
        
        for i, (img_path, target_size) in enumerate(zip(image_paths, target_sizes)):
            try:
                # Metal GPUでリサイズ
                resized_img = self.resize_image(img_path, target_size)
                
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
                except:
                    pass
        
        return results
```

### 3. ビデオエンコーディングのGPU最適化

```python
# commands/metal_video_encoder.py (新規作成)

import cv2
import numpy as np
import subprocess
import os
import time
import Metal
from typing import Callable, List, Tuple, Optional

class MetalVideoEncoder:
    """Metal GPUを活用したビデオエンコーダー"""
    
    def __init__(self, use_videotoolbox=True):
        """
        初期化
        
        Args:
            use_videotoolbox (bool): VideoToolboxを使用するか
        """
        self.use_videotoolbox = use_videotoolbox
        
        # VideoToolboxが利用可能か確認
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.videotoolbox_available = "h264_videotoolbox" in result.stdout
        except:
            self.videotoolbox_available = False
        
        print(f"Metal VideoEncoder初期化: VideoToolbox={'利用可能' if self.videotoolbox_available else '利用不可'}")
    
    def encode_frames_to_video(self, 
                              frame_generator: Callable[[int], np.ndarray],
                              output_file: str, 
                              frame_count: int,
                              fps: int = 30,
                              resolution: Tuple[int, int] = (1920, 1080),
                              bitrate: str = "5M",
                              preset: str = "faster"):
        """
        フレーム生成関数からビデオを生成
        
        Args:
            frame_generator: フレーム生成関数
            output_file: 出力ファイルパス
            frame_count: フレーム数
            fps: フレームレート
            resolution: 解像度
            bitrate: ビットレート
            preset: エンコードプリセット
            
        Returns:
            bool: 成功したかどうか
        """
        width, height = resolution
        
        # 最適なエンコーダーを選択
        if self.use_videotoolbox and self.videotoolbox_available:
            encoder = "h264_videotoolbox"
            encoder_options = [
                "-b:v", bitrate,
                "-allow_sw", "1",
                "-realtime", "false",
                "-profile:v", "high"
            ]
        else:
            encoder = "libx264"
            encoder_options = [
                "-preset", preset,
                "-crf", "23",
                "-b:v", bitrate
            ]
        
        # FFmpegコマンドを構築
        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", str(fps),
            "-i", "-"  # 標準入力から読み込み
        ]
        
        cmd.extend(["-c:v", encoder])
        cmd.extend(encoder_options)
        cmd.extend(["-pix_fmt", "yuv420p", output_file])
        
        try:
            # タイミング計測用
            start_time = time.time()
            frames_encoded = 0
            
            # サブプロセスを開始
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8  # 大きいバッファサイズ
            )
            
            # フレームを生成してパイプに送信
            for i in range(frame_count):
                frame = frame_generator(i)
                
                # RGBフォーマットに変換
                if frame.shape[2] == 4:  # RGBA形式
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                elif frame.shape[2] == 3 and frame.dtype == np.uint8:
                    if cv2.COLOR_BGR2RGB != 0:  # OpenCVが使うBGRフォーマット
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # バイトデータに変換
                process.stdin.write(frame.tobytes())
                frames_encoded += 1
                
                # 進捗表示
                if i % 10 == 0 or i == frame_count - 1:
                    elapsed = time.time() - start_time
                    fps_real = frames_encoded / elapsed if elapsed > 0 else 0
                    remaining = (frame_count - i - 1) / fps_real if fps_real > 0 else 0
                    print(f"エンコード進捗: {i+1}/{frame_count} フレーム処理済み " + 
                          f"({fps_real:.1f} fps, 残り約{remaining:.1f}秒)")
            
            # 入力を閉じて出力を待機
            process.stdin.close()
            process.wait()
            
            # 完了時間を表示
            total_time = time.time() - start_time
            print(f"エンコード完了: {total_time:.2f}秒 (平均{frames_encoded/total_time:.1f} fps)")
            
            return process.returncode == 0
            
        except Exception as e:
            print(f"エンコードエラー: {e}")
            return False
```

### 4. メイン処理のGPU最適化実装

```python
# commands/execute.py の変更部分

from commands.metal_image_processor import MetalImageProcessor
from commands.metal_video_encoder import MetalVideoEncoder

def main():
    # 既存のコード...
    
    # Metal GPU処理の初期化
    try:
        gpu_processor = MetalImageProcessor()
        gpu_available = True
        print("Metal GPU処理を使用します")
    except Exception as e:
        print(f"Metal GPU初期化エラー: {e}")
        print("CPU処理にフォールバックします")
        gpu_available = False
    
    # 環境変数からGPU使用の設定を取得
    USE_GPU = os.getenv('USE_GPU', 'true').lower() == 'true'
    
    # GPUを使用して画像処理（利用可能かつ有効な場合）
    if gpu_available and USE_GPU:
        # 画像サイズのリストを作成
        aspect_ratio = ASPECT_RATIO_W / ASPECT_RATIO_H
        target_heights = [IMAGE_HEIGHT] * len(image_files_list)
        target_widths = [int(IMAGE_HEIGHT * aspect_ratio)] * len(image_files_list)
        target_sizes = list(zip(target_widths, target_heights))
        
        # GPU処理を実行
        print(f"Metal GPUで{len(image_files_list)}枚の画像を処理しています...")
        temp_image_files = gpu_processor.process_batch(image_files_list, target_sizes)
    else:
        # 既存のCPU処理コード...
    
    # 以下のコードは既存のまま...
    
    # エンコーディング部分の修正
    if gpu_available and USE_GPU:
        try:
            # GPUエンコーダー初期化
            encoder = MetalVideoEncoder(use_videotoolbox=USE_VIDEOTOOLBOX)
            
            # フレーム生成関数の定義
            def generate_frame(frame_idx):
                # フレーム時間点の計算
                t = frame_idx / (FPS * ANIMATION_DURATION)
                
                # スライド位置を計算
                position = make_slide_animation(t)
                
                # 合成処理用に背景を作成
                frame = np.zeros((final_height, final_width, 3), dtype=np.uint8)
                frame[:] = BACKGROUND_COLOR  # 背景色を設定
                
                # グリッドの位置を設定
                x, y = position
                x_int, y_int = int(x), int(y)
                
                # グリッドが画面内にある場合のみ描画
                if (x_int < final_width and x_int + frame_w > 0 and 
                    y_int < final_height and y_int + frame_h > 0):
                    
                    # グリッド画像を合成
                    grid_img = grid_composite.get_frame(t)
                    
                    # 画面内の部分だけを合成
                    x_start = max(0, x_int)
                    y_start = max(0, y_int)
                    x_end = min(final_width, x_int + frame_w)
                    y_end = min(final_height, y_int + frame_h)
                    
                    grid_x_start = max(0, -x_int)
                    grid_y_start = max(0, -y_int)
                    grid_x_end = grid_x_start + (x_end - x_start)
                    grid_y_end = grid_y_start + (y_end - y_start)
                    
                    frame[y_start:y_end, x_start:x_end] = grid_img[
                        grid_y_start:grid_y_end, grid_x_start:grid_x_end
                    ]
                
                return frame
            
            # GPUを使用してビデオエンコーディング
            print("Metal GPUを使用してビデオをエンコードしています...")
            success = encoder.encode_frames_to_video(
                generate_frame,
                OUTPUT_FILENAME,
                frame_count=int(FPS * ANIMATION_DURATION),
                fps=FPS,
                resolution=(final_width, final_height),
                bitrate=BITRATE,
                preset=FFMPEG_PRESET
            )
            
            if not success:
                raise Exception("GPUエンコーディングに失敗しました")
                
        except Exception as e:
            print(f"GPUエンコーディングエラー: {e}")
            print("標準エンコーディングにフォールバックします...")
            # 既存のエンコーディング処理を実行...
    else:
        # 既存のエンコーディング処理を実行...
```

## GPU最適化のための.env設定

```
# GPU最適化設定
USE_GPU=true
GPU_MEMORY_LIMIT=4096
USE_VIDEOTOOLBOX=true
METAL_OPTIMIZE_LEVEL=3
```

## 追加のGPU最適化テクニック

### 1. 複数テクスチャの並列処理

```python
def process_multiple_textures(self, textures, operation):
    """
    複数テクスチャを並列処理
    
    Args:
        textures (list): テクスチャのリスト
        operation (callable): 各テクスチャに適用する操作
    
    Returns:
        list: 処理結果のリスト
    """
    results = []
    command_buffer = self.core.command_queue.commandBuffer()
    
    for texture in textures:
        result = operation(command_buffer, texture)
        results.append(result)
    
    command_buffer.commit()
    command_buffer.waitUntilCompleted()
    
    return results
```

### 2. プリコンパイル済みシェーダーの活用

```python
def compile_shader_library():
    """
    カスタムシェーダーをコンパイル
    """
    # シェーダーコード
    shader_code = """
    #include <metal_stdlib>
    using namespace metal;
    
    kernel void apply_filter(texture2d<float, access::read> inTexture [[texture(0)]],
                             texture2d<float, access::write> outTexture [[texture(1)]],
                             uint2 gid [[thread_position_in_grid]])
    {
        // テクスチャの境界チェック
        if (gid.x >= outTexture.get_width() || gid.y >= outTexture.get_height()) {
            return;
        }
        
        float4 color = inTexture.read(gid);
        
        // フィルタ処理
        color.rgb = 1.0 - color.rgb;  // 色反転の例
        
        outTexture.write(color, gid);
    }
    """
    
    # シェーダーライブラリのコンパイル
    options = Metal.MTLCompileOptions.alloc().init()
    library = self.core.device.newLibraryWithSource_options_error_(shader_code, options, None)
    
    return library
```

### 3. GPU使用効率の詳細モニタリング

```python
def monitor_gpu_usage():
    """
    GPUリソース使用状況をモニタリング
    """
    # MacOS固有の方法でGPU使用率を取得
    try:
        import subprocess
        result = subprocess.run(["ioreg", "-l"], capture_output=True, text=True)
        # 必要な情報を解析
        # ...
    except:
        pass
```

## 実装手順

1. 新規モジュールの追加:
   - `commands/metal_core.py`
   - `commands/metal_image_processor.py`
   - `commands/metal_video_encoder.py`

2. 既存モジュールの修正:
   - `commands/execute.py`の画像処理とエンコーディング部分

3. 環境変数の追加:
   - `USE_GPU`
   - `GPU_MEMORY_LIMIT`
   - `METAL_OPTIMIZE_LEVEL`

4. 段階的実装:
   - まず画像処理をGPUに移行
   - 次にエンコーディングをGPUに移行
   - 最後に全体の最適化を実施

## パフォーマンス目標

- GPU使用率: 50%以上
- CPU使用率: 60%以下
- 処理時間: CPU処理の1/3以下

## 注意事項

- Apple GPUは統合型メモリを使用するため、RAMとGPUメモリを効率的に共有管理する
- Metal API呼び出しのオーバーヘッドを最小限に抑えるため、できるだけ少ない呼び出しで処理をバッチ化する
- エラーが発生した場合は必ずCPU処理にフォールバックする仕組みを実装する
- プロファイリングを行い、ボトルネックを特定して最適化する
- 最新のmacOSと互換性があることを確認する（Metal APIのバージョン依存性に注意） 