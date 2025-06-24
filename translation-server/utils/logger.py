"""
ログ設定とログユーティリティ
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(log_level=logging.INFO):
    """ログ設定の初期化"""
    try:
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # スクリプトのディレクトリを取得
        script_dir = Path(os.path.abspath(__file__)).parent.parent
        
        # ログファイルのパス
        log_file = script_dir / "python-log.txt"
        
        # ファイルハンドラーを追加
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logging.getLogger().addHandler(file_handler)
        except Exception as e:
            print(f"ログファイルの設定エラー: {e}")
            
        # ロガーを返す
        return logging.getLogger()
    except Exception as e:
        print(f"ロギング設定エラー: {e}")
        # エラーが発生してもデフォルトのロガーを返す
        return logging.getLogger()


def get_logger(name):
    """名前付きロガーを取得"""
    return logging.getLogger(name)


class LoggerMixin:
    """ログ機能を提供するMixinクラス"""
    
    def log_message(self, message, level='INFO'):
        """ログメッセージを記録（GUI表示も考慮）"""
        # 標準ログ出力
        if level == 'ERROR':
            logging.error(message)
        elif level == 'WARNING':
            logging.warning(message)
        else:
            logging.info(message)
        
        # GUI表示用（必要に応じてオーバーライド）
        if hasattr(self, '_log_to_gui'):
            self._log_to_gui(message, level)

