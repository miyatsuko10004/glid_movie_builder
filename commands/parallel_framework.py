#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
parallel_framework.py

このスクリプトは、メモリ使用量と処理速度を最適化した並列処理フレームワークを提供します。
CPU使用率99.9%の問題を解決し、処理時間を大幅に短縮します。
"""

import os
import time
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Callable, List, Any, Dict, Union
import psutil
import gc
import platform
from tqdm import tqdm

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
        
        # ワーカー数の自動決定
        if worker_count is None:
            # Apple Siliconチップの場合は特別な処理
            if self._is_apple_silicon():
                # M1/M2/M3チップでは効率コアとパフォーマンスコアを考慮
                self.worker_count = min(self.cpu_count, 8)
            else:
                # 通常は利用可能なCPUコアの75%を使用
                self.worker_count = max(1, int(self.cpu_count * 0.75))
        else:
            self.worker_count = min(worker_count, self.cpu_count)
        
        self.use_threads_for_io = use_threads_for_io
        self.memory_limit_percent = memory_limit_percent
        
        # システム情報を出力
        self._print_system_info()
    
    def _is_apple_silicon(self):
        """Apple Siliconチップかどうかを判定"""
        if platform.system() != "Darwin":
            return False
            
        try:
            cpu_info = os.popen('sysctl -n machdep.cpu.brand_string').read().strip()
            return "Apple" in cpu_info
        except:
            return False
    
    def _print_system_info(self):
        """システム情報をログ出力"""
        mem = psutil.virtual_memory()
        print(f"並列処理フレームワーク初期化:")
        print(f"- CPU: {self.cpu_count}コア (使用: {self.worker_count}ワーカー)")
        print(f"- メモリ: {mem.total / (1024**3):.1f}GB (使用制限: {self.memory_limit_percent}%)")
        print(f"- プラットフォーム: {platform.system()} {platform.release()}")
        
        if self._is_apple_silicon():
            print("- Apple Siliconチップを検出しました")
    
    def _check_memory(self):
        """メモリ使用状況をチェックし、必要に応じてGCを実行"""
        current_mem = psutil.virtual_memory().percent
        if current_mem > self.memory_limit_percent:
            print(f"メモリ使用率が高いです: {current_mem}% > {self.memory_limit_percent}%")
            print("ガベージコレクションを実行します...")
            gc.collect()
            time.sleep(0.5)  # GC完了を待機
    
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
        # 実行前にメモリ状況をログ
        start_mem = psutil.virtual_memory()
        print(f"処理開始時メモリ: {start_mem.percent}% ({start_mem.used/(1024**3):.1f}GB/{start_mem.total/(1024**3):.1f}GB)")
        
        # 処理結果格納用
        results = []
        total_items = len(items)
        
        # 並列処理の実行
        print(f"並列処理を開始: {total_items}アイテム, バッチサイズ={batch_size}")
        
        # 処理タイプに応じたExecutorを選択
        executor_class = ThreadPoolExecutor if io_bound or self.use_threads_for_io else ProcessPoolExecutor
        
        # バッチごとに処理
        with tqdm(total=total_items, desc="バッチ処理") as pbar:
            for i in range(0, total_items, batch_size):
                # メモリチェック
                self._check_memory()
                
                # 現在のバッチを取得
                end_idx = min(i + batch_size, total_items)
                batch = items[i:end_idx]
                batch_size_actual = len(batch)
                
                # 定期的にメモリ使用状況をログ
                if i % (batch_size * 5) == 0 or i == 0:
                    mem = psutil.virtual_memory()
                    print(f"バッチ開始 {i}-{end_idx}: メモリ使用率 {mem.percent}% ({mem.used/(1024**3):.1f}GB)")
                
                batch_results = []
                
                # 並列処理エグゼキュータを作成
                with executor_class(max_workers=self.worker_count) as executor:
                    # 全てのタスクをスケジュール
                    futures = [executor.submit(process_func, item, *args, **kwargs) for item in batch]
                    
                    # 結果を収集
                    for future in futures:
                        try:
                            result = future.result()
                            if result is not None:
                                batch_results.append(result)
                        except Exception as e:
                            print(f"並列処理エラー: {e}")
                
                # バッチ結果を全体結果に追加
                results.extend(batch_results)
                
                # 進捗バーを更新
                pbar.update(batch_size_actual)
                
                # バッチ処理終了後にGCを実行する
                if batch_size_actual >= 10:
                    gc.collect()
        
        # 処理終了後にメモリ状況をログ
        end_mem = psutil.virtual_memory()
        print(f"処理終了時メモリ: {end_mem.percent}% ({end_mem.used/(1024**3):.1f}GB/{end_mem.total/(1024**3):.1f}GB)")
        
        return results
    
    def process_with_callback(
        self,
        items: List[Any],
        process_func: Callable,
        callback_func: Callable,
        io_bound: bool = False,
        max_workers: int = None,
        *args, **kwargs
    ) -> None:
        """
        コールバック付きの並列処理を実行する
        
        Args:
            items: 処理するアイテムのリスト
            process_func: 処理関数
            callback_func: 各アイテム処理後に呼ばれるコールバック関数
            io_bound: IO主体の処理かどうか
            max_workers: 最大ワーカー数（指定がなければ自動設定）
            *args, **kwargs: 処理関数への追加引数
        """
        if max_workers is None:
            max_workers = self.worker_count
        
        # 処理タイプに応じたExecutorを選択
        executor_class = ThreadPoolExecutor if io_bound or self.use_threads_for_io else ProcessPoolExecutor
        
        # コールバック関数の設定
        def _callback_wrapper(future):
            try:
                result = future.result()
                if result is not None:
                    callback_func(result)
            except Exception as e:
                print(f"コールバック処理エラー: {e}")
        
        # 並列処理を実行
        with executor_class(max_workers=max_workers) as executor:
            # 各アイテムをスケジュール
            futures = []
            for item in items:
                future = executor.submit(process_func, item, *args, **kwargs)
                future.add_done_callback(_callback_wrapper)
                futures.append(future)
            
            # 全てのタスクが完了するまで待機
            for future in futures:
                try:
                    future.result()
                except Exception:
                    # エラーはコールバックラッパーで処理される
                    pass 