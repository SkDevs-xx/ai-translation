"""
セキュリティ管理：APIキーの暗号化と復号化
"""

import json
import base64
import hashlib
import logging
from pathlib import Path
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class SecurityManager:
    """APIキーなどの機密情報を暗号化して保存するためのクラス"""
    
    def __init__(self, script_dir):
        self.script_dir = Path(script_dir)
        self.settings_file = self.script_dir / "settings.enc"
        self._encryption_key = None
    
    def _get_machine_key(self):
        """マシン固有の情報から暗号化キーを生成"""
        if self._encryption_key is None:
            # マシン固有の情報を組み合わせてキーを生成
            import platform
            machine_info = f"{platform.node()}{platform.machine()}{platform.processor()}"
            # ハッシュ化してキーを生成
            key_hash = hashlib.sha256(machine_info.encode()).digest()
            # Fernet用のキーに変換
            self._encryption_key = base64.urlsafe_b64encode(key_hash)
        return self._encryption_key
    
    def encrypt_data(self, data):
        """データを暗号化"""
        try:
            fernet = Fernet(self._get_machine_key())
            encrypted_data = fernet.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"暗号化エラー: {e}")
            return None
    
    def decrypt_data(self, encrypted_data):
        """データを復号化"""
        try:
            fernet = Fernet(self._get_machine_key())
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"復号化エラー: {e}")
            return None
    
    def save_settings(self, settings_dict):
        """設定を暗号化してファイルに保存"""
        try:
            # JSONとして文字列化
            settings_json = json.dumps(settings_dict, ensure_ascii=False, indent=2)
            
            # 暗号化
            encrypted_settings = self.encrypt_data(settings_json)
            if encrypted_settings is None:
                return False
            
            # ファイルに保存
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_settings)
            
            return True
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            return False
    
    def load_settings(self):
        """暗号化された設定ファイルを読み込み"""
        try:
            if not self.settings_file.exists():
                return {}
            
            # ファイルから読み込み
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                encrypted_settings = f.read().strip()
            
            # 復号化
            settings_json = self.decrypt_data(encrypted_settings)
            if settings_json is None:
                return {}
            
            # JSONとしてパース
            return json.loads(settings_json)
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
            return {}
    
    def save_api_key(self, api_key):
        """APIキーを保存"""
        settings = self.load_settings()
        settings['api_key'] = api_key
        return self.save_settings(settings)
    
    def load_api_key(self):
        """APIキーを読み込み"""
        settings = self.load_settings()
        return settings.get('api_key', None)
    
    def save_custom_prompt(self, prompt):
        """カスタムプロンプトを保存"""
        settings = self.load_settings()
        settings['custom_prompt'] = prompt
        return self.save_settings(settings)
    
    def load_custom_prompt(self):
        """カスタムプロンプトを読み込み"""
        settings = self.load_settings()
        return settings.get('custom_prompt', None)