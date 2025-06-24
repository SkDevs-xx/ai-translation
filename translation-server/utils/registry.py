"""
Windows レジストリ操作：自動起動設定
"""

import sys
import os
import winreg
import logging
from pathlib import Path
from core.config import APP_NAME

logger = logging.getLogger(__name__)


def get_exe_path():
    """実行ファイルのパスを取得"""
    if getattr(sys, 'frozen', False):
        # PyInstallerでビルドされた場合
        return sys.executable
    else:
        # 開発環境の場合
        return os.path.abspath(sys.argv[0])


def set_auto_start(enabled=True):
    """Windows起動時の自動起動を設定"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            if enabled:
                exe_path = get_exe_path()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
                logger.info(f"自動起動を有効化: {exe_path}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("自動起動を無効化")
                except FileNotFoundError:
                    pass
        
        return True
    except Exception as e:
        logger.error(f"自動起動設定エラー: {e}")
        return False


def is_auto_start_enabled():
    """自動起動が有効か確認"""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            try:
                winreg.QueryValueEx(key, APP_NAME)
                return True
            except FileNotFoundError:
                return False
    except Exception:
        return False