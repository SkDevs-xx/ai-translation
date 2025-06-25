"""
サーバー管理：Flask サーバーの起動/停止とステータス管理
"""

import threading
import logging
import time
from flask import Flask
from server.app import create_app, setup_routes
from server.handlers import APIHandlers
from translation.processor import TranslationProcessor
from core.config import SERVER_PORT

logger = logging.getLogger(__name__)


class ServerManager:
    """サーバー管理クラス"""
    
    def __init__(self, security_manager):
        self.security_manager = security_manager
        self.app = None
        self.server_thread = None
        self.is_running_flag = False
        self.handlers = None
        self.translation_processor = TranslationProcessor(security_manager)
        
    def start_server(self):
        """サーバーを起動"""
        if self.is_running_flag:
            logger.warning("サーバーは既に起動しています")
            return
        
        try:
            # Flask アプリケーションを作成
            self.app = create_app()
            
            # ハンドラーを初期化
            self.handlers = APIHandlers(self.security_manager)
            self.handlers.set_translation_processor(self.translation_processor)
            
            # ルートを設定
            setup_routes(self.app, self.handlers)
            
            # サーバースレッドを開始
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True
            )
            self.server_thread.start()
            
            # サーバーが起動するまで待機
            time.sleep(1)
            
            self.is_running_flag = True
            logger.info(f"サーバーを起動しました (ポート: {SERVER_PORT})")
            
        except Exception as e:
            logger.error(f"サーバー起動エラー: {e}")
            self.is_running_flag = False
            raise
    
    def _run_server(self):
        """サーバーを実行"""
        try:
            from werkzeug.serving import make_server
            
            # Werkzeugサーバーを作成
            self.server = make_server('0.0.0.0', SERVER_PORT, self.app)
            
            # ログを無効化（GUIログに統合）
            import sys
            import io
            sys.stderr = io.StringIO()
            
            # サーバーを実行
            self.server.serve_forever()
            
        except Exception as e:
            logger.error(f"サーバー実行エラー: {e}")
            self.is_running_flag = False
    
    def stop_server(self):
        """サーバーを停止"""
        if not self.is_running_flag:
            logger.warning("サーバーは起動していません")
            return
        
        try:
            self.is_running_flag = False
            
            # サーバーをシャットダウン
            if hasattr(self, 'server'):
                self.server.shutdown()
            
            # スレッドの終了を待機
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            logger.info("サーバーを停止しました")
            
        except Exception as e:
            logger.error(f"サーバー停止エラー: {e}")
    
    def is_running(self):
        """サーバーが実行中かチェック"""
        return self.is_running_flag
    
    def get_current_prompt(self):
        """現在の翻訳プロンプトを取得"""
        return self.translation_processor.get_prompt()
    
    def set_prompt(self, prompt):
        """翻訳プロンプトを設定"""
        self.translation_processor.set_prompt(prompt)
        logger.info("翻訳プロンプトを更新しました")
    
    def cleanup_old_files(self):
        """古いファイルをクリーンアップ"""
        if self.handlers:
            self.handlers.cleanup_old_files()