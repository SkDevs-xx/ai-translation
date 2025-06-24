"""
APIハンドラー：Flask APIエンドポイントの実装
"""

import os
import json
import time
import logging
from pathlib import Path
from flask import jsonify, send_file
from werkzeug.exceptions import BadRequest
from core.config import TEMP_DIR, JSON_DIR
from utils.audio_downloader import AudioDownloader
from translation.processor import TranslationProcessor

logger = logging.getLogger(__name__)


class APIHandlers:
    """API エンドポイントハンドラー"""
    
    def __init__(self, security_manager):
        self.security_manager = security_manager
        self.audio_downloader = AudioDownloader(TEMP_DIR)
        self.translation_processor = None
        
        # ディレクトリの作成
        os.makedirs(TEMP_DIR, exist_ok=True)
        os.makedirs(JSON_DIR, exist_ok=True)
    
    def set_translation_processor(self, processor):
        """翻訳プロセッサーを設定"""
        self.translation_processor = processor
    
    def handle_download(self, video_id):
        """音声ダウンロードと翻訳処理"""
        try:
            if not video_id:
                raise BadRequest("video_id is required")
            
            # API キーの取得と検証
            api_key = self.security_manager.load_api_key()
            if not api_key:
                return jsonify({
                    'error': 'API key not configured. Please set up your API key in the application.'
                }), 401
            
            # 既存のJSONファイルをチェック
            json_path = Path(JSON_DIR) / f"{video_id}.json"
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        logger.info(f"既存の翻訳データを返却: {video_id}")
                        return jsonify(existing_data)
                except Exception as e:
                    logger.error(f"既存JSONファイルの読み込みエラー: {e}")
            
            # 進捗更新コールバック
            def progress_callback(percent):
                # TODO: WebSocketやSSEで進捗を通知する実装を追加可能
                logger.debug(f"ダウンロード進捗: {percent}%")
            
            # 音声ダウンロード
            success, result = self.audio_downloader.download_audio(video_id, progress_callback)
            if not success:
                return jsonify({'error': result}), 500
            
            audio_path = result['path']
            video_title = result['title']
            
            # 翻訳処理
            if not self.translation_processor:
                return jsonify({'error': 'Translation processor not initialized'}), 500
            
            translate_result = self.translation_processor.translate_audio(
                audio_path, video_id, api_key
            )
            
            if not translate_result['success']:
                return jsonify({'error': translate_result['error']}), 500
            
            # 結果を保存
            result_data = translate_result['data']
            
            # タイトルとタイムスタンプを追加
            from datetime import datetime
            result_data['title'] = video_title
            result_data['timestamp'] = datetime.now().isoformat()
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"翻訳完了: {video_id}")
            return jsonify(result_data)
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"ダウンロードエラー: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def handle_delete_json(self, video_id):
        """保存された翻訳データを削除"""
        try:
            if not video_id:
                raise BadRequest("video_id is required")
            
            json_path = Path(JSON_DIR) / f"{video_id}.json"
            
            if not json_path.exists():
                return jsonify({'error': 'File not found'}), 404
            
            json_path.unlink()
            logger.info(f"翻訳データを削除: {video_id}")
            
            return jsonify({'success': True, 'message': f'Deleted {video_id}.json'})
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"削除エラー: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def handle_read_json(self, video_id):
        """保存された翻訳データを読み込み"""
        try:
            if not video_id:
                raise BadRequest("video_id is required")
            
            json_path = Path(JSON_DIR) / f"{video_id}.json"
            
            if not json_path.exists():
                return jsonify({'error': 'File not found'}), 404
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return jsonify(data)
            
        except BadRequest as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"読み込みエラー: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    def handle_health(self):
        """ヘルスチェックエンドポイント"""
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'api_key_configured': bool(self.security_manager.load_api_key())
        })
    
    def cleanup_old_files(self):
        """古いファイルのクリーンアップ"""
        self.audio_downloader.cleanup_old_files()