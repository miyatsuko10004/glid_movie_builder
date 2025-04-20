# グリッド動画生成ツール メモリ最適化プロンプト

## 目的
16GBのRAMを搭載した環境で、メモリリソースを最大限に活用し処理速度を向上させる最適化を実装する。

## 現状の課題
- `MEMORY_BATCH_SIZE`のデフォルト値が30と低く設定されている
- メモリ使用率の上限が85%と控えめに設定されている
- 並列ワーカー数が最大6と、16GBメモリ環境では少なすぎる
- メモリ内処理よりもディスクI/Oが多く発生している

## メモリ最適化の方針

### 1. バッチサイズと並列処理の最適化

```python
# .env設定
MEMORY_BATCH_SIZE=70     # 現在の30から大幅に増加
THREAD_COUNT=10          # スレッド数を増加
MEMORY_THRESHOLD=92      # メモリ使用率の上限を92%に
RAM_DISK_SIZE=6G         # 6GBのRAMディスクを使用
```

```python
# commands/optimize_utils.py の修正
def process_with_memory_optimization(items, batch_size, process_batch_func, *args, **kwargs):
    """
    メモリ使用量を最適化してバッチ処理を行います。
    
    Args:
        items (list): 処理する項目のリスト
        batch_size (int): バッチサイズ
        process_batch_func (function): バッチ処理関数
        *args, **kwargs: 処理関数への追加の引数
        
    Returns:
        list: 処理結果のリスト
    """
    results = []
    total_items = len(items)
    
    # メモリ監視のためのしきい値
    memory_threshold = int(os.getenv('MEMORY_THRESHOLD', 92))  # 環境変数から閾値を取得、デフォルトは92%
    
    # 利用可能なメモリの表示
    total_mem = psutil.virtual_memory().total / (1024 * 1024 * 1024)
    print(f"利用可能なメモリ: {total_mem:.1f} GB")
    print(f"メモリ使用率上限: {memory_threshold}%")
    
    with tqdm(total=total_items, desc="バッチ処理") as pbar:
        for i in range(0, total_items, batch_size):
            # メモリ使用状況をチェック
            current_mem = psutil.virtual_memory().percent
            if current_mem > memory_threshold:
                import gc
                print(f"メモリ使用率 {current_mem}% が閾値を超えました。GCを実行します...")
                gc.collect()
                time.sleep(0.5)  # システムがメモリを解放する時間を与える
            
            end_idx = min(i + batch_size, total_items)
            batch = items[i:end_idx]
            
            # 現在のメモリ使用状況をログ
            if i % (batch_size * 3) == 0:
                mem = psutil.virtual_memory()
                print(f"メモリ状態: {mem.percent}% 使用中 ({mem.used/(1024**3):.1f}GB/{mem.total/(1024**3):.1f}GB)")
            
            # バッチを処理
            batch_results = process_batch_func(batch, *args, **kwargs)
            results.extend(batch_results)
            
            pbar.update(len(batch))
    
    return results
```

### 2. RAMディスクの活用

```python
# commands/ram_disk_utils.py (新規作成)

import os
import subprocess
import shutil
import tempfile
import platform
import psutil

def setup_ram_disk(mount_point=None, size="6G"):
    """
    RAMディスクをセットアップします。
    
    Args:
        mount_point (str): マウントポイント（Noneの場合は自動生成）
        size (str): サイズ（例: "6G"）
        
    Returns:
        str: RAMディスクのパス
    """
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
        subprocess.run(["diskutil", "unmount", mount_point], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

def cleanup_ram_disk(mount_point):
    """
    RAMディスクをクリーンアップします。
    
    Args:
        mount_point (str): RAMディスクのマウントポイント
    """
    if platform.system() != "Darwin":
        return
    
    try:
        subprocess.run(["diskutil", "unmount", mount_point], check=False)
        print(f"RAMディスクをアンマウントしました: {mount_point}")
    except Exception as e:
        print(f"RAMディスクのアンマウントに失敗しました: {e}")
```

### 3. メモリ内処理の最適化

```python
# commands/execute.py の修正部分

# RAMディスクの使用
from commands.ram_disk_utils import setup_ram_disk, cleanup_ram_disk

def main():
    # 既存のコード...
    
    # RAMディスクのセットアップ
    ram_disk_size = os.getenv('RAM_DISK_SIZE', '6G')
    temp_dir = setup_ram_disk(size=ram_disk_size)
    print(f"一時ファイル用RAMディスク: {temp_dir}")
    
    try:
        # GCの最適化（処理前に一度実行して以降は最小限に）
        import gc
        gc.collect()
        
        # 処理中はGCを無効化してパフォーマンスを向上
        gc.disable()
        
        # メモリバッチサイズを環境に応じて調整
        memory_info = psutil.virtual_memory()
        total_gb = memory_info.total / (1024**3)
        print(f"システムメモリ: {total_gb:.1f}GB")
        
        # メモリ容量に基づいてバッチサイズを動的に調整
        if total_gb >= 32:
            adjusted_batch_size = 120
        elif total_gb >= 16:
            adjusted_batch_size = 70
        else:
            adjusted_batch_size = MEMORY_BATCH_SIZE
        
        print(f"調整されたバッチサイズ: {adjusted_batch_size}")
        
        # 以降は既存の処理を実行...
        # ただし、一時ファイルの保存先をRAMディスクに変更
        
        # 処理完了後にGCを再度有効化
        gc.enable()
        gc.collect()
        
    finally:
        # RAMディスクのクリーンアップ
        cleanup_ram_disk(temp_dir)
```

### 4. プロファイリングと動的調整

```python
# commands/memory_profiler.py (新規作成)

import time
import threading
import psutil
import os
import numpy as np
from collections import deque

class MemoryProfiler:
    """メモリ使用状況をモニタリングするプロファイラー"""
    
    def __init__(self, interval=1.0, history_size=60):
        """
        初期化
        
        Args:
            interval (float): サンプリング間隔（秒）
            history_size (int): 履歴サイズ
        """
        self.interval = interval
        self.running = False
        self.thread = None
        self.memory_history = deque(maxlen=history_size)
        self.cpu_history = deque(maxlen=history_size)
        self.start_time = None
        self.peak_memory = 0
        self.peak_memory_time = 0
    
    def start(self):
        """モニタリングを開始"""
        if self.running:
            return
        
        self.running = True
        self.start_time = time.time()
        self.peak_memory = 0
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("メモリプロファイリングを開始しました")
    
    def stop(self):
        """モニタリングを停止"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        
        self._print_summary()
    
    def _monitor_loop(self):
        """モニタリングループ"""
        while self.running:
            try:
                # メモリ使用状況を取得
                mem = psutil.virtual_memory()
                mem_percent = mem.percent
                mem_used_gb = mem.used / (1024**3)
                
                # CPU使用率を取得
                cpu_percent = psutil.cpu_percent(interval=None)
                
                # 履歴に追加
                self.memory_history.append(mem_percent)
                self.cpu_history.append(cpu_percent)
                
                # ピークメモリを更新
                if mem_percent > self.peak_memory:
                    self.peak_memory = mem_percent
                    self.peak_memory_time = time.time() - self.start_time
                
                # 一定間隔でログ出力
                elapsed = time.time() - self.start_time
                if int(elapsed) % 30 == 0:  # 30秒ごとにログ出力
                    print(f"[{elapsed:.1f}秒] メモリ: {mem_percent:.1f}% ({mem_used_gb:.1f}GB), CPU: {cpu_percent:.1f}%")
                
                time.sleep(self.interval)
            except Exception as e:
                print(f"モニタリングエラー: {e}")
                break
    
    def _print_summary(self):
        """サマリーを表示"""
        elapsed = time.time() - self.start_time
        
        if not self.memory_history:
            print("モニタリングデータがありません")
            return
        
        avg_memory = np.mean(self.memory_history)
        avg_cpu = np.mean(self.cpu_history)
        
        print("\n===== メモリプロファイリング結果 =====")
        print(f"実行時間: {elapsed:.1f}秒")
        print(f"平均メモリ使用率: {avg_memory:.1f}%")
        print(f"平均CPU使用率: {avg_cpu:.1f}%")
        print(f"ピークメモリ使用率: {self.peak_memory:.1f}% (実行{self.peak_memory_time:.1f}秒後)")
        
        # メモリ使用率の傾向分析
        if len(self.memory_history) >= 10:
            recent_avg = np.mean(list(self.memory_history)[-10:])
            if recent_avg > avg_memory * 1.1:
                print("警告: メモリ使用率が増加傾向にあります")
        
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        print(f"現在のメモリ状態: {mem.percent:.1f}% 使用中 ({mem.used/(1024**3):.1f}GB/{mem.total/(1024**3):.1f}GB)")
        print(f"スワップ使用状況: {swap.percent:.1f}% ({swap.used/(1024**3):.1f}GB/{swap.total/(1024**3):.1f}GB)")
        print("========================================")

# 使用例
# profiler = MemoryProfiler()
# profiler.start()
# try:
#     # 処理を実行
#     main()
# finally:
#     profiler.stop()
```

## 実装手順

1. 環境変数の追加（`.env`ファイル）:
   ```
   # 16GB RAM向け最適化設定
   MEMORY_BATCH_SIZE=70
   THREAD_COUNT=10
   MEMORY_THRESHOLD=92
   RAM_DISK_SIZE=6G
   USE_GPU=true
   GPU_MEMORY_LIMIT=4096
   STREAM_PROCESSING=true
   ```

2. 新規ユーティリティの追加:
   - `commands/ram_disk_utils.py`
   - `commands/memory_profiler.py`

3. 既存のモジュール修正:
   - `commands/optimize_utils.py`の`process_with_memory_optimization`関数
   - `commands/execute.py`のメモリ管理部分

4. Metal GPU処理との統合:
   - RAMディスクをGPU処理の一時ファイル保存に使用
   - GPUメモリとRAMの連携最適化

## メモリ使用パターンの最適化

1. **フロントロード戦略**:
   - 処理開始時に積極的にメモリを確保し、中間データを効率的に保持
   - 処理後半でメモリを段階的に解放

2. **動的バッチサイズ調整**:
   - メモリ使用状況に応じてバッチサイズを動的に増減
   - メモリ使用率が低い場合はバッチサイズを増加、高い場合は減少

3. **優先度ベースのメモリ管理**:
   - 重要な処理には多くのメモリを割り当て
   - 重要度の低い処理は小さなバッチで実行

## モニタリングと分析

1. メモリプロファイラーを使用して実行時の詳細なメモリ使用状況を記録
2. 16GB環境で最適なバッチサイズとスレッド数を見極める
3. 処理中のメモリリークを検出して修正

## 最適値の判断基準

| メモリサイズ | 推奨バッチサイズ | 推奨スレッド数 | 最大メモリ使用率 |
|--------------|-----------------|---------------|-----------------|
| 8GB以下      | 20-30           | 4-6           | 85%             |
| 16GB         | 60-80           | 8-12          | 90-92%          |
| 32GB以上     | 100-120         | 12-16         | 95%             |

## 注意事項

- スワップの発生を避けるため、メモリ使用率の上限（92%）を超えないよう監視する
- システム安定性を確保するため定期的にメモリ状態をチェックする仕組みを組み込む
- RAMディスクの使用は処理終了時に必ず解放する
- GPU処理と並列処理のバランスを取り、両方のリソースを最大限に活用する 