# グリッド動画生成ツール デバッグ・解析プロンプト

## 目的
グリッド動画生成ツールの性能問題を診断し、実行時の問題やボトルネックを特定して最適な改善策を提案する。

## 現状の問題
- CPU使用率が99.9%と極めて高い
- 処理時間が1時間以上かかる
- GPU（Metal）リソースが活用されていない
- スレッド数が2と非常に少ない

## デバッグ・解析アプローチ

### 1. プロファイリング実施

```python
import cProfile
import pstats
import io

def profile_execution():
    """
    実行をプロファイリングし、最も時間がかかっている関数を特定する
    """
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 既存のメイン処理を呼び出す
    main()
    
    profiler.disable()
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(30)  # 上位30個の関数を表示
    
    print(s.getvalue())
    
    # 結果をファイルに保存
    with open('profile_results.txt', 'w') as f:
        f.write(s.getvalue())

if __name__ == "__main__":
    profile_execution()
```

### 2. メモリ使用量モニタリング

```python
import tracemalloc
import time
import os
import psutil

def monitor_memory_usage():
    """
    メモリ使用量をモニタリングし、メモリリークや過剰使用を検出する
    """
    process = psutil.Process(os.getpid())
    tracemalloc.start()
    
    # 初期状態を記録
    snapshot1 = tracemalloc.take_snapshot()
    initial_memory = process.memory_info().rss / 1024 / 1024
    print(f"初期メモリ使用量: {initial_memory:.2f} MB")
    
    # 既存の処理を実行
    main()
    
    # 実行後の状態を記録
    snapshot2 = tracemalloc.take_snapshot()
    final_memory = process.memory_info().rss / 1024 / 1024
    print(f"最終メモリ使用量: {final_memory:.2f} MB")
    print(f"メモリ増加: {final_memory - initial_memory:.2f} MB")
    
    # 差分を分析
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    print("[ メモリ使用量の多い上位10個の差分 ]")
    for stat in top_stats[:10]:
        print(stat)
```

### 3. ボトルネック分析

```python
import time
from functools import wraps

# 計測用デコレータ
def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        print(f"関数 {func.__name__} の実行時間: {elapsed_time:.4f} 秒")
        return result
    return wrapper

# 主要な関数に適用する例
@measure_time
def process_image_parallel(img_path, aspect_ratio_w, aspect_ratio_h, crop_position, image_height):
    # 既存の実装
    pass

@measure_time
def make_slide_animation(t):
    # 既存の実装
    pass
```

### 4. GPU使用状況診断

```python
def diagnose_gpu_capabilities():
    """
    Metal GPUの利用可能性と使用状況を診断する
    """
    # pyobjcがインストールされているか確認
    try:
        import Metal
        import MetalPerformanceShaders
        print("Metal APIが利用可能です")
        
        # デバイス情報を取得
        device = Metal.MTLCreateSystemDefaultDevice()
        if device:
            print(f"Metal デバイス名: {device.name()}")
            print(f"ヒープリソース使用可能: {'はい' if device.hasUnifiedMemory() else 'いいえ'}")
            print(f"低電力モード: {'はい' if device.isLowPower() else 'いいえ'}")
        else:
            print("Metal デバイスが取得できません")
    except ImportError:
        print("Metal APIが利用できません。pyobjcパッケージが必要です。")
        print("インストール方法: pip install pyobjc")
```

### 5. ストレステスト

```python
def run_stress_test(image_count=100, image_size=(1920, 1080)):
    """
    異なる条件下でのパフォーマンスを測定するストレステスト
    """
    import numpy as np
    from PIL import Image
    import tempfile
    import shutil
    import os
    
    # テスト用一時ディレクトリを作成
    test_dir = tempfile.mkdtemp(prefix="glid_stress_test_")
    try:
        # テスト用画像を生成
        print(f"{image_count}枚のテスト画像を生成中...")
        for i in range(1, image_count + 1):
            # ランダムカラーの画像を生成
            array = np.random.randint(0, 255, (*image_size, 3), dtype=np.uint8)
            img = Image.fromarray(array)
            img.save(os.path.join(test_dir, f"image_{i:02d}.jpeg"))
        
        # 異なる設定でテスト実行
        configurations = [
            {"GRID_ROWS": 6, "GRID_COLS": 6, "ANIMATION_DURATION": 4},
            {"GRID_ROWS": 8, "GRID_COLS": 8, "ANIMATION_DURATION": 4},
            {"GRID_ROWS": 10, "GRID_COLS": 10, "ANIMATION_DURATION": 4},
            {"GRID_ROWS": 6, "GRID_COLS": 6, "ANIMATION_DURATION": 8},
        ]
        
        for config in configurations:
            # 環境変数を設定
            for key, value in config.items():
                os.environ[key] = str(value)
            
            print(f"設定でテスト実行中: {config}")
            # 時間計測
            start_time = time.time()
            main()  # メイン処理の実行
            elapsed_time = time.time() - start_time
            
            print(f"実行時間: {elapsed_time:.2f}秒")
            # CPU/メモリ使用状況を記録
            # ...
    finally:
        # テスト用一時ディレクトリを削除
        shutil.rmtree(test_dir)
```

## 解析のためのチェックリスト

1. **CPU使用率**
   - `top`または`htop`コマンドでリアルタイムモニタリング
   - スレッド数と各スレッドの負荷を確認

2. **メモリ使用量**
   - 仮想メモリとRSSメモリの使用状況
   - 大きなオブジェクトの割り当てとリーク

3. **I/O操作**
   - 一時ファイルの読み書き回数
   - ディスクI/Oのボトルネック

4. **GPU使用率**
   - Metal APIの呼び出し状況
   - GPUメモリ使用量

5. **スレッド状態**
   - デッドロックや競合条件の検出
   - スレッドプールの効率性

## 改善ステップ

1. プロファイリング結果に基づいて最もコストの高い関数を最適化
2. GPU処理の効率的な実装
3. 並列処理フレームワークの再設計
4. メモリ管理の最適化
5. エンコーディングパイプラインの効率化

## 注意事項
- デバッグコードが結果に影響を与えないよう注意
- 適切なタイミングでプロファイリングを開始・終了
- テスト用のデータセットと本番データを分離
- 複数の環境でテストを実施して結果を比較 