# グリッド動画生成ツール最適化プロンプト

## 目的
グリッド動画生成ツールの処理速度を改善し、CPU使用率99.9%の状態を最適化して、より効率的な動画生成を実現する。

## 現状の問題点
- CPU使用率が99.9%と高負荷状態が続いている
- 処理時間が非常に長い（1時間以上）
- GPU（Metal）のリソースが十分に活用されていない
- スレッド数が少なく（2スレッド）、マルチコア処理が不十分
- 画像処理とエンコーディングのパイプラインに非効率な部分がある

## 最適化の方向性

### 1. Metal GPU活用の強化
- pyobjcとMetalフレームワークを使用したGPU処理の実装
- 主要な画像処理操作（リサイズ、フィルタリング、合成）をGPUに移行
- GPUメモリ管理の最適化

```python
# Metal GPUを活用した画像処理の例
def process_image_with_metal(image_path, target_size):
    # Metalデバイスの初期化
    device = Metal.MTLCreateSystemDefaultDevice()
    if device is None:
        return fallback_process_image(image_path, target_size)
    
    # ここにMetal処理コードを実装
    # ...
    
    return processed_image
```

### 2. 並列処理の最適化
- スレッド数を現在の2から8-16に増加
- タスク分割の最適化（IO操作、CPU処理、GPU処理の並列化）
- 効率的なワークスチーリングアルゴリズムの実装

```python
def optimize_parallel_processing():
    # 最適なワーカー数の決定
    cpu_count = os.cpu_count()
    optimal_workers = max(8, min(16, cpu_count))
    
    # 処理の種類に応じたプール作成
    io_pool = ThreadPoolExecutor(max_workers=optimal_workers)
    cpu_pool = ProcessPoolExecutor(max_workers=optimal_workers)
    
    # タスクの分散
    # ...
```

### 3. メモリ管理の改善
- 大きな画像のストリーミング処理導入
- メモリマッピングの活用
- 一時ファイルの最小化とRAMディスク活用

```python
def optimize_memory_usage():
    # RAMディスクの設定
    ram_disk_path = "/private/tmp/glid_processing"
    setup_ram_disk(ram_disk_path, size="2G")
    
    # メモリマッピングの活用
    # ...
```

### 4. エンコーディングパイプラインの効率化
- MoviePyの中間ステップを削減し、FFmpegを直接制御
- フレーム生成とエンコードの統合
- スライディングウィンドウ方式の導入

```python
def create_optimized_pipeline():
    # FFmpegパイプラインの設定
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",  # 標準入力からのパイプ
        "-c:v", "h264_videotoolbox",  # Appleハードウェアエンコーダー
        "-b:v", "5M",
        "-pix_fmt", "yuv420p",
        output_file
    ]
    
    # フレーム生成とエンコードのパイプライン連結
    # ...
```

### 5. アルゴリズム最適化
- 効率的なフレーム差分計算の導入
- 計算集約的な部分をJITコンパイル（Numba）
- 再計算を避けるキャッシングメカニズム

```python
import numba

@numba.jit(nopython=True, parallel=True)
def calculate_frame_positions(frame_count, duration, speed):
    # 高速な位置計算
    positions = np.zeros((frame_count, 2), dtype=np.float32)
    for i in numba.prange(frame_count):
        t = i / frame_count * duration
        progress = t / duration * speed
        positions[i, 0] = width - (width + frame_w) * progress
        positions[i, 1] = (height - frame_h) // 2 if height > frame_h else 0
    return positions
```

## 設定パラメータの最適化

```
# .env設定例
PARALLEL_PROCESSING=true
USE_VIDEOTOOLBOX=true
THREAD_COUNT=8
MEMORY_BATCH_SIZE=20
USE_GPU=true
GPU_MEMORY_LIMIT=2048
STREAM_PROCESSING=true
FRAME_CACHING=true
TEMP_DIR=/private/tmp/glid_processing
```

## 実装手順
1. Metal GPUサポートの完全実装
2. 並列処理フレームワークの再設計
3. メモリ管理の最適化
4. エンコーディングパイプラインの効率化
5. 全体的なパフォーマンステストと調整

## 評価指標
- 処理時間: 現在の1/5以下を目標
- CPU使用率: 平均60%以下を目標
- GPU使用率: 50%以上を目標
- メモリ使用量: 現在の2GB以下を維持

## プロファイリングと継続的最適化
- 各モジュールの処理時間を測定
- ボトルネックを特定して集中的に最適化
- 異なるハードウェア構成での動作検証

## 注意事項
- 最適化により視覚的な品質が低下しないよう注意
- ファイル互換性とユーザーインターフェースの一貫性を維持
- エラー処理を強化して安定性を確保 