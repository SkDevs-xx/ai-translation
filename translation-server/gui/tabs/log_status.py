"""
ログ・ステータスタブ：サーバー状態、ログ表示、翻訳ファイル管理
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import queue
import os
import json
import webbrowser
from datetime import datetime
from pathlib import Path
from core.config import SERVER_PORT, JSON_DIR

logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """カスタムログハンドラー"""
    
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
    
    def emit(self, record):
        log_entry = self.format(record)
        self.queue.put(log_entry)


class LogStatusTab:
    """ログ・ステータスタブクラス"""
    
    def __init__(self, parent, server_manager, security_manager):
        self.server_manager = server_manager
        self.security_manager = security_manager
        
        # フレーム作成
        self.frame = ttk.Frame(parent)
        
        # ログキュー
        self.log_queue = queue.Queue()
        
        # メインコンテナ
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 上部フレーム（サーバーステータスと翻訳管理）
        upper_frame = ttk.Frame(main_container)
        upper_frame.pack(fill="x", pady=(0, 10))
        
        # 上部を水平に配置
        # サーバーステータスセクション
        self._create_server_status_section(upper_frame)
        
        # 翻訳ファイル管理セクション
        self._create_translations_section(upper_frame)
        
        # 下部フレーム（ログ表示）
        lower_frame = ttk.Frame(main_container)
        lower_frame.pack(fill="both", expand=True)
        self._create_log_section(lower_frame)
        
        # ログハンドラーを設定
        self._setup_log_handler()
        
        # 定期的にログを更新
        self._update_logs()
        
        # 初期状態を更新
        self.update_server_status()
        self.refresh_translations_list()
    
    def _create_server_status_section(self, parent):
        """サーバーステータスセクションを作成"""
        # ステータスフレーム
        status_frame = ttk.LabelFrame(parent, text="サーバーステータス", padding="10")
        
        # 内容フレーム
        content_frame = ttk.Frame(status_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # サーバー状態
        ttk.Label(content_frame, text="状態:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.status_label = ttk.Label(content_frame, text="停止中", font=('', 10, 'bold'))
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        # ポート番号
        ttk.Label(content_frame, text="ポート:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        port_label = ttk.Label(content_frame, text=str(SERVER_PORT))
        port_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # URL
        ttk.Label(content_frame, text="URL:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        url_label = ttk.Label(content_frame, text=f"http://localhost:{SERVER_PORT}")
        url_label.grid(row=2, column=1, sticky=tk.W, pady=(5, 0))
        
        # API キー状態
        ttk.Label(content_frame, text="API キー:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.api_key_status_label = ttk.Label(content_frame, text="")
        self.api_key_status_label.grid(row=3, column=1, sticky=tk.W, pady=(5, 0))
        
        # ボタンフレーム
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill="x", pady=(20, 10))
        
        # 起動/停止ボタン
        self.toggle_button = ttk.Button(
            button_frame,
            text="サーバーを起動",
            command=self._toggle_server,
            width=20
        )
        self.toggle_button.pack(side="left", padx=(10, 5))
        
        # 再起動ボタン
        self.restart_button = ttk.Button(
            button_frame,
            text="再起動",
            command=self._restart_server,
            width=20,
            state=tk.DISABLED
        )
        self.restart_button.pack(side="left", padx=5)
        
        status_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # API キー状態を更新
        self.update_api_key_status()
    
    def _create_translations_section(self, parent):
        """翻訳ファイル管理セクションを作成"""
        # 翻訳管理フレーム
        trans_frame = ttk.LabelFrame(parent, text="保存された翻訳", padding="10")
        
        # リストボックスフレーム
        list_frame = ttk.Frame(trans_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # リストボックスとスクロールバー
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.translations_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=8
        )
        self.translations_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.translations_listbox.yview)
        
        # リストボックスのイベント
        self.translations_listbox.bind('<<ListboxSelect>>', self._on_translation_select)
        
        # 情報ラベル
        self.translation_info_label = ttk.Label(trans_frame, text="", wraplength=300)
        self.translation_info_label.pack(fill="x", padx=10, pady=(0, 10))
        
        # ボタンフレーム
        button_frame = ttk.Frame(trans_frame)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # 更新ボタン
        refresh_button = ttk.Button(
            button_frame,
            text="リスト更新",
            command=self.refresh_translations_list,
            width=15
        )
        refresh_button.pack(side="left", padx=(0, 5))
        
        # YouTubeで開くボタン
        self.open_youtube_button = ttk.Button(
            button_frame,
            text="YouTubeで開く",
            command=self._open_in_youtube,
            width=15,
            state=tk.DISABLED
        )
        self.open_youtube_button.pack(side="left", padx=5)
        
        # 削除ボタン
        self.delete_button = ttk.Button(
            button_frame,
            text="削除",
            command=self._delete_selected_translation,
            width=10,
            state=tk.DISABLED
        )
        self.delete_button.pack(side="left", padx=5)
        
        trans_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        # 翻訳データを保持
        self.translations_data = {}
    
    def _create_log_section(self, parent):
        """ログ表示セクションを作成"""
        # ログフレーム
        log_frame = ttk.LabelFrame(parent, text="ログ", padding="10")
        log_frame.pack(fill="both", expand=True)
        
        # ログ表示エリア
        log_display_frame = ttk.Frame(log_frame)
        log_display_frame.pack(fill="both", expand=True)
        
        # テキストウィジェット
        self.log_text = tk.Text(
            log_display_frame,
            height=10,
            wrap=tk.WORD,
            font=('Consolas', 9)
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        
        # スクロールバー
        log_scrollbar = ttk.Scrollbar(log_display_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # タグ設定（ログレベルごとの色分け）
        self.log_text.tag_configure('DEBUG', foreground='gray')
        self.log_text.tag_configure('INFO', foreground='black')
        self.log_text.tag_configure('WARNING', foreground='orange')
        self.log_text.tag_configure('ERROR', foreground='red')
        self.log_text.tag_configure('CRITICAL', foreground='red', background='yellow')
        
        # 読み取り専用に設定
        self.log_text.configure(state=tk.DISABLED)
        
        # コントロールフレーム
        control_frame = ttk.Frame(log_frame)
        control_frame.pack(fill="x", pady=(10, 0))
        
        # 自動スクロール
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(
            control_frame,
            text="自動スクロール",
            variable=self.auto_scroll_var
        )
        auto_scroll_check.pack(side="left", padx=(0, 20))
        
        # クリアボタン
        clear_button = ttk.Button(
            control_frame,
            text="ログをクリア",
            command=self._clear_logs,
            width=15
        )
        clear_button.pack(side="left")
    
    def _toggle_server(self):
        """サーバーの起動/停止を切り替え"""
        if self.server_manager.is_running():
            self._stop_server()
        else:
            self._start_server()
    
    def _start_server(self):
        """サーバーを起動"""
        def start_thread():
            try:
                self.toggle_button.config(state=tk.DISABLED, text="起動中...")
                self.server_manager.start_server()
                self.update_server_status()
            except Exception as e:
                logger.error(f"サーバー起動エラー: {e}")
                self.update_server_status()
        
        threading.Thread(target=start_thread, daemon=True).start()
    
    def _stop_server(self):
        """サーバーを停止"""
        def stop_thread():
            try:
                self.toggle_button.config(state=tk.DISABLED, text="停止中...")
                self.server_manager.stop_server()
                self.update_server_status()
            except Exception as e:
                logger.error(f"サーバー停止エラー: {e}")
                self.update_server_status()
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    def _restart_server(self):
        """サーバーを再起動"""
        def restart_thread():
            try:
                self.toggle_button.config(state=tk.DISABLED)
                self.restart_button.config(state=tk.DISABLED, text="再起動中...")
                
                self.server_manager.stop_server()
                self.update_server_status()
                
                import time
                time.sleep(1)  # 少し待機
                
                self.server_manager.start_server()
                self.update_server_status()
            except Exception as e:
                logger.error(f"サーバー再起動エラー: {e}")
                self.update_server_status()
        
        threading.Thread(target=restart_thread, daemon=True).start()
    
    def update_server_status(self):
        """サーバーステータスを更新"""
        if self.server_manager.is_running():
            self.status_label.config(text="✓ 稼働中", foreground="green")
            self.toggle_button.config(text="サーバーを停止", state=tk.NORMAL)
            self.restart_button.config(state=tk.NORMAL, text="再起動")
        else:
            self.status_label.config(text="✗ 停止中", foreground="red")
            self.toggle_button.config(text="サーバーを起動", state=tk.NORMAL)
            self.restart_button.config(state=tk.DISABLED, text="再起動")
    
    def update_api_key_status(self):
        """APIキーステータスを更新"""
        if self.security_manager.load_api_key():
            self.api_key_status_label.config(text="✓ 設定済み", foreground="green")
        else:
            self.api_key_status_label.config(text="⚠ 未設定", foreground="orange")
    
    def refresh_translations_list(self):
        """翻訳リストを更新"""
        self.translations_listbox.delete(0, tk.END)
        self.translations_data.clear()
        
        # JSONディレクトリを確認
        json_dir = Path(JSON_DIR)
        if not json_dir.exists():
            return
        
        # JSONファイルを読み込み
        for json_file in json_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                video_id = json_file.stem
                title = data.get('title', 'Unknown')
                
                # リストに追加
                display_text = f"{video_id} - {title[:50]}..."
                self.translations_listbox.insert(tk.END, display_text)
                
                # データを保持
                self.translations_data[video_id] = data
                
            except Exception as e:
                logger.error(f"JSONファイル読み込みエラー ({json_file}): {e}")
    
    def _on_translation_select(self, event):
        """翻訳選択時の処理"""
        selection = self.translations_listbox.curselection()
        if not selection:
            return
        
        # 選択されたアイテムのテキストから動画IDを抽出
        selected_text = self.translations_listbox.get(selection[0])
        video_id = selected_text.split(' - ')[0]
        
        if video_id in self.translations_data:
            data = self.translations_data[video_id]
            
            # 情報を表示
            title = data.get('title', 'Unknown')
            subtitle_count = len(data.get('subtitles', []))
            timestamp = data.get('timestamp', '')
            
            info_text = f"タイトル: {title}\n字幕数: {subtitle_count}個\n作成日時: {timestamp}"
            self.translation_info_label.config(text=info_text)
            
            # ボタンを有効化
            self.open_youtube_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
            
            # 現在選択中の動画IDを保持
            self.selected_video_id = video_id
    
    def _open_in_youtube(self):
        """YouTubeで動画を開く"""
        if hasattr(self, 'selected_video_id'):
            url = f"https://www.youtube.com/watch?v={self.selected_video_id}"
            webbrowser.open(url)
    
    def _delete_selected_translation(self):
        """選択した翻訳を削除"""
        if not hasattr(self, 'selected_video_id'):
            return
        
        video_id = self.selected_video_id
        title = self.translations_data[video_id].get('title', 'Unknown')
        
        # 確認ダイアログ
        result = messagebox.askyesno(
            "削除の確認",
            f"以下の翻訳データを削除しますか？\n\n動画ID: {video_id}\nタイトル: {title}"
        )
        
        if result:
            try:
                json_path = Path(JSON_DIR) / f"{video_id}.json"
                json_path.unlink()
                
                # リストを更新
                self.refresh_translations_list()
                
                # 情報をクリア
                self.translation_info_label.config(text="")
                self.open_youtube_button.config(state=tk.DISABLED)
                self.delete_button.config(state=tk.DISABLED)
                
                messagebox.showinfo("成功", "翻訳データを削除しました")
                
            except Exception as e:
                logger.error(f"削除エラー: {e}")
                messagebox.showerror("エラー", f"削除に失敗しました: {str(e)}")
    
    def _setup_log_handler(self):
        """ログハンドラーを設定"""
        # カスタムハンドラーを作成
        self.log_handler = LogHandler(self.log_queue)
        self.log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # ルートロガーに追加
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
    
    def _update_logs(self):
        """ログを定期的に更新"""
        # キューからログを取得
        while not self.log_queue.empty():
            try:
                log_entry = self.log_queue.get_nowait()
                self._append_log_entry(log_entry)
            except queue.Empty:
                break
        
        # 100ms後に再度実行
        self.frame.after(100, self._update_logs)
    
    def _append_log_entry(self, log_entry):
        """ログエントリを追加"""
        # ログレベルを判定
        level = None
        for lvl in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
            if f' - {lvl} - ' in log_entry:
                level = lvl
                break
        
        # テキストを有効化
        self.log_text.configure(state=tk.NORMAL)
        
        # ログを追加
        if level:
            self.log_text.insert(tk.END, log_entry + '\n', level)
        else:
            self.log_text.insert(tk.END, log_entry + '\n')
        
        # 自動スクロール
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        # テキストを無効化
        self.log_text.configure(state=tk.DISABLED)
    
    def _clear_logs(self):
        """ログをクリア"""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def append_log(self, message):
        """外部からログを追加"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} - GUI - INFO - {message}"
        self.log_queue.put(log_entry)