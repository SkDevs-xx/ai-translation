"""
メインウィンドウ：GUIのメインフレームとレイアウト管理
"""

import tkinter as tk
from tkinter import ttk
import threading
import logging
from core.config import APP_NAME, APP_VERSION
from gui.tabs.basic_settings import BasicSettingsTab
from gui.tabs.log_status import LogStatusTab

logger = logging.getLogger(__name__)


class MainWindow:
    """メインウィンドウクラス"""
    
    def __init__(self, server_manager, security_manager):
        self.server_manager = server_manager
        self.security_manager = security_manager
        self.root = None
        self.notebook = None
        self.tabs = {}
        
    def create_window(self):
        """メインウィンドウを作成"""
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("650x800")
        
        # アイコン設定
        self._set_app_icon()
        
        # ウィンドウを閉じた時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # グリッドの設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # ノートブック（タブコンテナ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タブの作成
        self._create_tabs()
        
        return self.root
    
    def _create_tabs(self):
        """各タブを作成"""
        # 基本設定タブ
        self.tabs['basic_settings'] = BasicSettingsTab(
            self.notebook, 
            self.security_manager,
            self.server_manager,
            self.on_api_key_saved
        )
        self.notebook.add(self.tabs['basic_settings'].frame, text="基本設定")
        
        # ログ・ステータスタブ
        self.tabs['log_status'] = LogStatusTab(
            self.notebook,
            self.server_manager,
            self.security_manager
        )
        self.notebook.add(self.tabs['log_status'].frame, text="ログ・ステータス")
    
    def _set_app_icon(self):
        """アプリケーションアイコンを設定"""
        try:
            import sys
            import os
            
            if getattr(sys, 'frozen', False):
                # PyInstallerでビルドされた場合
                base_path = sys._MEIPASS
            else:
                # 開発環境の場合
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            icon_paths = [
                os.path.join(base_path, "icons", "icons-128.png"),
                os.path.join(base_path, "icons", "icons-48.png"),
                os.path.join(base_path, "icons", "icons-16.png"),
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        icon = tk.PhotoImage(file=icon_path)
                        self.root.iconphoto(True, icon)
                        logger.info(f"アイコンを設定: {icon_path}")
                        break
                    except Exception as e:
                        logger.warning(f"アイコン設定エラー ({icon_path}): {e}")
        except Exception as e:
            logger.warning(f"アイコン設定をスキップ: {e}")
    
    def on_api_key_saved(self):
        """APIキーが保存された時の処理"""
        # ログ・ステータスタブのAPIキーステータスを更新
        if 'log_status' in self.tabs:
            self.tabs['log_status'].update_api_key_status()
    
    def append_log(self, message):
        """ログ・ステータスタブにメッセージを追加"""
        if 'log_status' in self.tabs:
            self.tabs['log_status'].append_log(message)
    
    def _on_closing(self):
        """ウィンドウを閉じる時の処理"""
        # サーバーを停止
        if self.server_manager.is_running():
            self.server_manager.stop_server()
        
        # ウィンドウを破棄
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """メインループを開始"""
        self.root.mainloop()