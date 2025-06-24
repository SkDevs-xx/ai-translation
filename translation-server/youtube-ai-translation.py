#!/usr/bin/env python3
"""
YouTube AI Translation Server with GUI - Modular Version
Chrome拡張機能と連携してYouTube動画の音声を高速ダウンロード・翻訳
GUI + タスクトレイ対応版
"""

import sys
import os
import logging
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import win32event
import win32api
import winerror

# 内部モジュール
from core.config import APP_NAME, APP_VERSION, SERVER_PORT
from core.security import SecurityManager
from server.manager import ServerManager
from gui.main_window import MainWindow
from utils.logger import setup_logging

# 外部ライブラリ
import pystray
from PIL import Image, ImageDraw

# ログ設定
logger = setup_logging()


class YouTubeTranslatorApp:
    """メインアプリケーションクラス"""
    
    def __init__(self):
        # 実行ファイルのディレクトリを取得
        if getattr(sys, 'frozen', False):
            self.exe_dir = Path(os.path.dirname(sys.executable))
        else:
            self.exe_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        
        # マネージャーを初期化
        self.security_manager = SecurityManager(self.exe_dir)
        self.server_manager = ServerManager(self.security_manager)
        self.main_window = None
        self.tray_icon = None
        self.root = None
        
        # 定期タスク用
        self.cleanup_timer = None
    
    def create_tray_icon(self):
        """タスクトレイアイコンを作成"""
        # アイコン画像を作成（または既存のアイコンを使用）
        icon_path = self.exe_dir / "icons" / "icons-16.png"
        
        if icon_path.exists():
            try:
                image = Image.open(icon_path)
            except Exception as e:
                logger.warning(f"アイコン読み込みエラー: {e}")
                image = self._create_default_icon()
        else:
            image = self._create_default_icon()
        
        # メニューを作成
        menu = pystray.Menu(
            pystray.MenuItem("ウィンドウを表示", self.show_window, default=True),
            pystray.MenuItem("サーバーを開始", self.start_server_from_tray, 
                           lambda item: not self.server_manager.is_running()),
            pystray.MenuItem("サーバーを停止", self.stop_server_from_tray,
                           lambda item: self.server_manager.is_running()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", self.quit_app)
        )
        
        # アイコンを作成
        self.tray_icon = pystray.Icon(
            APP_NAME,
            image,
            f"{APP_NAME} v{APP_VERSION}",
            menu
        )
    
    def _create_default_icon(self):
        """デフォルトのアイコンを作成"""
        # 16x16の画像を作成
        width = height = 16
        image = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # 青い円を描画
        draw.ellipse([2, 2, 14, 14], fill=(0, 100, 255))
        
        # 白い文字 "T" を描画
        draw.text((5, 2), "T", fill=(255, 255, 255))
        
        return image
    
    def show_window(self, icon=None, item=None):
        """メインウィンドウを表示"""
        if self.root:
            self.root.deiconify()
            self.root.lift()
    
    def hide_window(self):
        """メインウィンドウを非表示"""
        if self.root:
            self.root.withdraw()
    
    def start_server_from_tray(self, icon=None, item=None):
        """トレイメニューからサーバーを起動"""
        try:
            self.server_manager.start_server()
            if self.main_window:
                self.main_window.tabs['log_status'].update_server_status()
        except Exception as e:
            logger.error(f"サーバー起動エラー: {e}")
    
    def stop_server_from_tray(self, icon=None, item=None):
        """トレイメニューからサーバーを停止"""
        try:
            self.server_manager.stop_server()
            if self.main_window:
                self.main_window.tabs['log_status'].update_server_status()
        except Exception as e:
            logger.error(f"サーバー停止エラー: {e}")
    
    def quit_app(self, icon=None, item=None):
        """アプリケーションを終了"""
        # サーバーを停止
        if self.server_manager.is_running():
            self.server_manager.stop_server()
        
        # タスクトレイアイコンを停止
        if self.tray_icon:
            self.tray_icon.stop()
        
        # GUIを終了
        if self.root:
            self.root.quit()
            self.root.destroy()
        
        # アプリケーションを終了
        sys.exit(0)
    
    def start_cleanup_timer(self):
        """定期的なクリーンアップタスクを開始"""
        def cleanup_task():
            try:
                self.server_manager.cleanup_old_files()
                logger.info("古いファイルのクリーンアップを実行しました")
            except Exception as e:
                logger.error(f"クリーンアップエラー: {e}")
            
            # 24時間後に再実行
            self.cleanup_timer = threading.Timer(24 * 60 * 60, cleanup_task)
            self.cleanup_timer.daemon = True
            self.cleanup_timer.start()
        
        # 初回実行
        cleanup_task()
    
    def run(self):
        """アプリケーションを実行"""
        logger.info(f"{APP_NAME} v{APP_VERSION} を起動しています...")
        
        try:
            # タスクトレイアイコンを作成
            logger.info("タスクトレイアイコンを作成中...")
            self.create_tray_icon()
            
            # タスクトレイアイコンを別スレッドで実行
            logger.info("タスクトレイアイコンをバックグラウンドで起動中...")
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
            
            # メインウィンドウを作成
            logger.info("メインウィンドウを作成中...")
            self.main_window = MainWindow(self.server_manager, self.security_manager)
            self.root = self.main_window.create_window()
            
            # ウィンドウクローズ時の動作を設定
            self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
            
            # 定期タスクを開始
            logger.info("定期タスクを開始中...")
            self.start_cleanup_timer()
            
            # サーバーを自動起動（APIキーが設定されている場合）
            if self.security_manager.load_api_key():
                try:
                    logger.info("サーバーを自動起動中...")
                    self.server_manager.start_server()
                    self.main_window.tabs['log_status'].update_server_status()
                    self.main_window.append_log("サーバーを自動起動しました")
                except Exception as e:
                    logger.error(f"サーバー自動起動エラー: {e}")
                    self.main_window.append_log(f"サーバー自動起動エラー: {e}")
            
            # メインループを開始
            logger.info("メインループを開始中...")
            self.main_window.run()
        except Exception as e:
            logger.error(f"実行時エラー: {e}", exc_info=True)
            raise


def check_single_instance():
    """アプリケーションの多重起動をチェック"""
    # ユニークな名前のミューテックスを作成
    mutex_name = f"Global\\{APP_NAME.replace(' ', '_')}_Mutex_{SERVER_PORT}"
    
    try:
        # ミューテックスの作成を試みる
        mutex = win32event.CreateMutex(None, False, mutex_name)
        
        # 既に存在する場合はエラーになる
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            # 既に起動している
            win32api.CloseHandle(mutex)
            return False
        
        # ミューテックスを保持（アプリケーション終了まで）
        return mutex
    except Exception as e:
        logger.error(f"ミューテックス作成エラー: {e}")
        return None


def main():
    """メイン関数"""
    # 多重起動チェック
    mutex = check_single_instance()
    if mutex is False:
        # 既に起動している場合
        messagebox.showwarning(
            "既に起動しています",
            f"{APP_NAME}は既に起動しています。\n"
            "タスクトレイのアイコンを確認してください。"
        )
        sys.exit(0)
    
    try:
        app = YouTubeTranslatorApp()
        app.run()
    except KeyboardInterrupt:
        print("\nアプリケーションを停止しています...")
    except Exception as e:
        # エラーの詳細をファイルに記録
        import traceback
        error_msg = f"エラーが発生しました: {e}\n{traceback.format_exc()}"
        print(error_msg)
        
        # エラーログファイルに記録
        try:
            if getattr(sys, 'frozen', False):
                exe_dir = Path(os.path.dirname(sys.executable))
            else:
                exe_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            
            error_file = exe_dir / "error.log"
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except:
            pass
        
        sys.exit(1)
    finally:
        # ミューテックスを解放
        if mutex and mutex is not False:
            win32api.CloseHandle(mutex)


if __name__ == '__main__':
    main()