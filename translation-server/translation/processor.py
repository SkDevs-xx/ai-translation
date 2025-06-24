"""
翻訳処理：Google Gemini APIを使用した音声翻訳
"""

import os
import json
import time
import logging
import re
from pathlib import Path
import google.generativeai as genai
from translation.subtitle import process_subtitles_with_end_times
from core.config import DEFAULT_PROMPT

logger = logging.getLogger(__name__)


class TranslationProcessor:
    """翻訳処理クラス"""
    
    def __init__(self):
        self.current_prompt = DEFAULT_PROMPT
    
    def set_prompt(self, prompt):
        """翻訳プロンプトを設定"""
        self.current_prompt = prompt
        logger.info("翻訳プロンプトを更新しました")
    
    def get_prompt(self):
        """現在のプロンプトを取得"""
        return self.current_prompt
    
    def translate_audio(self, audio_path, video_id, api_key):
        """
        音声ファイルを翻訳
        
        Args:
            audio_path: 音声ファイルのパス
            video_id: YouTube動画ID
            api_key: Gemini API キー
            
        Returns:
            dict: 結果 {'success': bool, 'data': dict or 'error': str}
        """
        uploaded_file = None
        
        try:
            # 音声ファイルの存在確認
            if not os.path.exists(audio_path):
                return {'success': False, 'error': f'Audio file not found: {audio_path}'}
            
            # ファイルサイズチェック
            file_size = os.path.getsize(audio_path)
            logger.info(f'音声データサイズ: {file_size / 1024 / 1024:.2f} MB')
            
            if file_size == 0:
                return {'success': False, 'error': '取得された音声データが空です'}
            
            if file_size < 1024:  # 1KB未満
                return {'success': False, 'error': f'取得された音声データが小さすぎます: {file_size} bytes'}
            
            # Gemini API設定
            genai.configure(api_key=api_key)
            
            # APIにアップロード
            logger.info('APIにアップロード中...')
            try:
                uploaded_file = genai.upload_file(path=audio_path, mime_type="audio/mp3")
                logger.info(f'アップロード完了。File URI: {uploaded_file.uri}')
            except Exception as upload_error:
                logger.error(f'アップロードエラー: {upload_error}')
                return {'success': False, 'error': f'APIへのアップロードに失敗: {upload_error}'}
            
            # Gemini APIで翻訳
            from core.config import GEMINI_MODEL_NAME
            model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            
            logger.info('APIで翻訳処理中...')
            response = model.generate_content([self.current_prompt, uploaded_file])
            logger.info('APIから応答がありました。JSON解析を開始します。')
            
            raw_text = response.text
            
            # JSON解析処理
            subtitles = self.parse_json_response(raw_text)
            
            if not subtitles:
                logger.error('有効な字幕オブジェクトを一つも解析できませんでした。')
                return {'success': False, 'error': 'APIからの応答を解析できませんでした。'}
            
            # 動画の長さを計算（最後の字幕の終了時刻）
            video_duration = subtitles[-1]['end'] if subtitles else 0
            minutes = int(video_duration / 60)
            seconds = int(video_duration % 60)
            
            logger.info(f'翻訳完了: {minutes}分{seconds}秒の動画から{len(subtitles)}件の字幕を生成')
            
            return {
                'success': True,
                'data': {
                    'video_id': video_id,
                    'subtitles': subtitles
                }
            }
            
        except Exception as e:
            logger.error(f"翻訳処理エラー: {e}")
            return {
                'success': False,
                'error': f'Translation error: {str(e)}'
            }
            
        finally:
            # アップロードファイルのクリーンアップ
            if uploaded_file:
                try:
                    genai.delete_file(uploaded_file.name)
                    logger.info('アップロードファイルを削除しました')
                except Exception as cleanup_error:
                    logger.error(f'ファイルクリーンアップエラー: {cleanup_error}')
    
    def parse_json_response(self, raw_text):
        """柔軟なJSONレスポンス解析とend時間の自動計算"""
        # まず全体をJSON配列として解析を試みる
        try:
            raw_subtitles = json.loads(raw_text)
            if isinstance(raw_subtitles, list):
                return process_subtitles_with_end_times(raw_subtitles)
        except (json.JSONDecodeError, ValueError):
            pass  # エラーは無視して個別解析に進む
        
        # 失敗した場合、個別のJSONオブジェクトを抽出
        raw_subtitles = []
        text = raw_text
        
        while True:
            # {の位置を探す
            start_pos = text.find('{')
            if start_pos == -1:
                break
            
            # 対応する}を探す（ネストを考慮）
            brace_count = 0
            end_pos = start_pos
            for i in range(start_pos, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i
                        break
            
            if end_pos > start_pos:
                obj_str = text[start_pos:end_pos+1]
                try:
                    # 時間形式の修正: "1:04.5" -> "64.5"
                    obj_str_fixed = re.sub(r'"(\d+):(\d+\.?\d*)"', lambda m: f'"{int(m.group(1))*60 + float(m.group(2))}"', obj_str)
                    
                    subtitle_obj = json.loads(obj_str_fixed)
                    # 必要なキーが含まれているか確認（start + textまたは従来のstart + end + text）
                    if 'start' in subtitle_obj and 'text' in subtitle_obj:
                        raw_subtitles.append(subtitle_obj)
                        logger.info(f'字幕オブジェクトを解析: start={subtitle_obj.get("start", 0)}秒')
                except json.JSONDecodeError as e:
                    logger.warning(f'JSONオブジェクトの解析に失敗: {obj_str[:100]}... エラー: {e}')
                
                # 次の検索のため、処理済み部分を削除
                text = text[end_pos+1:]
            else:
                break
        
        return process_subtitles_with_end_times(raw_subtitles)