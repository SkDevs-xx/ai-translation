#!/usr/bin/env python3
"""
YouTube Audio Downloader Server with GUI
Chrome拡張機能と連携してYouTube動画の音声を高速ダウンロード・翻訳
GUI + タスクトレイ対応版
"""

import sys
import os
import logging
import json
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import winreg
import webbrowser
import base64
import hashlib
from cryptography.fernet import Fernet
import re
import win32event
import win32api
import winerror

# 外部ライブラリ
from flask import Flask, jsonify, request
from flask_cors import CORS
import yt_dlp
import google.generativeai as genai
import pystray
from PIL import Image, ImageDraw

# ===== 設定 =====
APP_NAME = "YouTube AI Translation"
APP_VERSION = "2.0.0"
SERVER_PORT = 8888

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityManager:
    """APIキーなどの機密情報を暗号化して保存するためのクラス"""
    
    def __init__(self, exe_dir):
        self.exe_dir = Path(exe_dir)
        self.settings_file = self.exe_dir / "settings.enc"
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
    

class YouTubeTranslatorApp:
    # デフォルトプロンプト定数
    DEFAULT_PROMPT = """## You are a professional video translator.
## [Absolute Rules]
1. Output format
- Output should be in a JSON object array format only. Do not include any markdown or other text.
- Each object must have only two keys: `start` and `text`.

2. Time (start)
- The `start` value must be a string in "mm:ss" format (e.g., "0:05", "1:23", "12:45").
- Time must be monotonically increasing.
- Specify the exact timing when the speech begins.

3. Subtitle text (text)
- Use `\n` to break a line.
- Maximum of two lines per segment.
- Maximum of 25 characters per line is recommended for readability.
- Each segment should represent a complete thought or sentence.
- Do not break a line immediately after a comma (",", "、").
- Accurately reflect the intent and nuance of the original audio. Use natural and fluent Japanese, avoiding overly literal translations.
- Do not generate subtitles for silent sections, music-only sections, or audio fillers (e.g., "um", "uh", "er").

## [Output example: correct format]
[
{
"start": "0:05",
"text": "こんにちは皆さん。\n今日は素晴らしい日ですね。"
},
{
"start": "0:30",
"text": "はい、承知いたしました。\n詳しくご説明します。"
},
{
"start": "12:05",
"text": "これは非常に重要なポイントです。\n皆さんに覚えておいてほしいことがあります。"
}
]

"""

    def __init__(self):
        self.api_key = ""
        self.auto_start = False
        self.server_thread = None
        self.server_running = False
        self.custom_prompt = ""
        self.use_custom_prompt = False
        
        # セキュリティマネージャー初期化
        self.security_manager = SecurityManager(self.get_exe_dir())
        
        # Flask アプリの初期化
        self.app = Flask(__name__)
        CORS(self.app, origins=['chrome-extension://*', 'http://localhost:*'])
        self.setup_flask_routes()
        
        # GUI初期化
        self.setup_gui()
        
        # タスクトレイ初期化
        self.setup_system_tray()
        
        # 設定読み込み
        self.load_settings()
        
        # カスタムプロンプト読み込み
        self.load_custom_prompt_from_file()
        
        # プロンプト表示エリアの初期化
        self.initialize_prompt_display()
    
    def get_exe_dir(self):
        """実行ファイルのディレクトリを取得"""
        return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        
    def setup_flask_routes(self):
        """Flask ルートの設定"""
        
        @self.app.route('/')
        def index():
            return jsonify({
                'status': 'running',
                'service': APP_NAME,
                'version': APP_VERSION,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/health')
        def health_check():
            return jsonify({'status': 'ok'})
        
        @self.app.route('/download/<video_id>')
        def download_audio_route(video_id):
            return self.process_video(video_id)
        
        @self.app.route('/delete_json/<video_id>', methods=['DELETE'])
        def delete_json_file_route(video_id):
            return self.delete_json_file(video_id)
        
        @self.app.route('/read_json/<video_id>')
        def read_json_file_route(video_id):
            return self.read_json_file_direct(video_id)
    
    def process_video(self, video_id):
        """YouTube動画の音声をダウンロードして翻訳"""
        try:
            self.log_message(f'翻訳開始: {video_id}')
            
            # APIキーの確認
            if not self.api_key:
                raise Exception("APIキーが設定されていません")
            
            # genai設定
            genai.configure(api_key=self.api_key)
            
            uploaded_file = None
            
            try:
                # YouTube動画URLを構築
                video_url = f'https://www.youtube.com/watch?v={video_id}'
                self.log_message(f'動画URL: {video_url}')
                
                # yt-dlpで音声データを取得（メモリ上で処理）
                self.log_message(f'音声データ取得開始: {video_id}')
                
                import tempfile
                import io
                
                # 一時ファイルを使用（メモリ上で処理）
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                    temp_filename = temp_file.name
                
                ydl_opts = {
                    'format': 'bestaudio[abr>=128]/bestaudio',  # 128kbps以上
                    'outtmpl': temp_filename,
                    'overwrites': True,
                    'extract_flat': False,
                    'writeinfojson': False,
                    'writethumbnail': False,
                    'writesubtitles': False,
                    'ignoreerrors': False,
                }
                
                try:
                    # yt-dlpを実行してダウンロード
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info(video_url, download=True)
                        video_title = info_dict.get('title', 'Unknown')
                        
                    self.log_message(f'音声データ取得完了: {video_title}')
                    
                except Exception as download_error:
                    self.log_message(f'yt-dlp取得エラー: {download_error}', level='ERROR')
                    raise Exception(f"音声データの取得に失敗: {download_error}")
                
                # ファイルの存在確認
                if not os.path.exists(temp_filename):
                    raise Exception(f"音声データファイルが存在しません")
                
                # ファイルサイズチェック
                file_size = os.path.getsize(temp_filename)
                self.log_message(f'音声データサイズ: {file_size / 1024 / 1024:.2f} MB')
                
                # ファイルが空でないことを確認
                if file_size == 0:
                    raise Exception("取得された音声データが空です")
                
                if file_size < 1024:  # 1KB未満
                    raise Exception(f"取得された音声データが小さすぎます: {file_size} bytes")
                
                # APIにアップロード
                self.log_message('APIにアップロード中...')
                try:
                    uploaded_file = genai.upload_file(path=temp_filename, mime_type="audio/mp4")
                    self.log_message(f'アップロード完了。File URI: {uploaded_file.uri}')
                    
                    # 一時ファイルを削除
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                        self.log_message('一時ファイルを削除しました')
                    
                except Exception as upload_error:
                    self.log_message(f'アップロードエラー: {upload_error}', level='ERROR')
                    raise Exception(f"APIへのアップロードに失敗: {upload_error}")
                
                # Gemini APIで翻訳
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # プロンプトの選択（カスタムプロンプトがある場合はそれを使用）
                prompt = self.get_current_prompt()
                
                self.log_message('APIで翻訳処理中...')
                response = model.generate_content([prompt, uploaded_file])
                self.log_message('APIから応答がありました。JSON解析を開始します。')
                
                raw_text = response.text
                
                # JSON解析処理
                subtitles = self.parse_json_response(raw_text)
                
                if not subtitles:
                    self.log_message('有効な字幕オブジェクトを一つも解析できませんでした。', level='ERROR')
                    raise Exception("APIからの応答を解析できませんでした。")

                # 動画の長さを計算（最後の字幕の終了時刻）
                video_duration = subtitles[-1]['end'] if subtitles else 0
                minutes = int(video_duration / 60)
                seconds = int(video_duration % 60)
                
                self.log_message(f'翻訳完了: {minutes}分{seconds}秒の動画から{len(subtitles)}件の字幕を生成')
                
                self.save_to_json(video_id, subtitles, video_title)
                
                return jsonify({'success': True, 'subtitles': subtitles, 'title': video_title, 'video_id': video_id})
                
            finally:
                if uploaded_file:
                    try:
                        genai.delete_file(uploaded_file.name)
                        self.log_message('アップロードファイルを削除しました')
                    except Exception as cleanup_error:
                        self.log_message(f'ファイルクリーンアップエラー: {cleanup_error}', level='ERROR')
                
        except Exception as e:
            error_msg = str(e)
            self.log_message(f'エラー: {error_msg}', level='ERROR')
            return jsonify({'success': False, 'error': error_msg}), 500


    def save_to_json(self, video_id, subtitles, title):
        """字幕データをJSONファイルとして保存"""
        try:
            # 実行ファイルと同じディレクトリのjsonフォルダに保存
            json_dir = self.get_exe_dir() / "json"
            json_dir.mkdir(exist_ok=True)
            
            json_file = json_dir / f"{video_id}.json"
            
            data = {
                'video_id': video_id,
                'title': title,
                'timestamp': datetime.now().isoformat(),
                'subtitles': subtitles
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.log_message(f'JSONファイル保存: {json_file}')
            
        except Exception as e:
            self.log_message(f'JSONファイル保存エラー: {e}', level='ERROR')
    
    def parse_json_response(self, raw_text):
        """柔軟なJSONレスポンス解析とend時間の自動計算"""
        # まず全体をJSON配列として解析を試みる
        try:
            raw_subtitles = json.loads(raw_text)
            if isinstance(raw_subtitles, list):
                return self.process_subtitles_with_end_times(raw_subtitles)
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
                        self.log_message(f'字幕オブジェクトを解析: start={subtitle_obj.get("start", 0)}秒')
                except json.JSONDecodeError as e:
                    self.log_message(f'JSONオブジェクトの解析に失敗: {obj_str[:100]}... エラー: {e}', level='WARNING')
                
                # 次の検索のため、処理済み部分を削除
                text = text[end_pos+1:]
            else:
                break
        
        return self.process_subtitles_with_end_times(raw_subtitles)
    
    def convert_mmss_to_seconds(self, time_str):
        """mm:ss形式の文字列を秒数に変換"""
        try:
            if ':' in str(time_str):
                parts = str(time_str).split(':')
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
            # 既に数値の場合はそのまま返す（互換性維持）
            return float(time_str)
        except (ValueError, AttributeError):
            self.log_message(f'時間形式エラー: {time_str}', level='ERROR')
            return 0.0
    
    def process_subtitles_with_end_times(self, raw_subtitles):
        """字幕データにend時間を追加し、統合・制約を適用"""
        if not raw_subtitles:
            return []
        
        # mm:ss形式をまず秒数に変換
        for subtitle in raw_subtitles:
            if 'start' in subtitle:
                subtitle['start'] = self.convert_mmss_to_seconds(subtitle['start'])
            if 'end' in subtitle:
                subtitle['end'] = self.convert_mmss_to_seconds(subtitle['end'])
        
        # start時間でソート
        raw_subtitles.sort(key=lambda x: x.get('start', 0))
        
        # Step 1: 基本的なend時間計算（制約適用前）
        basic_subtitles = []
        for i, subtitle in enumerate(raw_subtitles):
            start_time = subtitle.get('start', 0)
            text = subtitle.get('text', '')
            
            # 既にend時間がある場合（従来形式との互換性）
            if 'end' in subtitle:
                end_time = subtitle['end']
            else:
                # end時間を自動計算
                if i < len(raw_subtitles) - 1:
                    # 次のセグメントの開始時間の0.1秒前
                    next_start = raw_subtitles[i + 1].get('start', start_time + 10)
                    end_time = next_start - 0.1
                else:
                    # 最後のセグメントは適切な長さを設定（最大10秒）
                    end_time = start_time + 8.0  # デフォルト8秒
            
            basic_subtitle = {
                'start': start_time,
                'end': end_time,
                'text': text
            }
            basic_subtitles.append(basic_subtitle)
        
        # Step 2: セグメント統合処理（制約適用前に実行）
        merged_subtitles = self.merge_short_segments_early(basic_subtitles)
        
        # Step 3: 最終的な制約適用
        final_subtitles = []
        for subtitle in merged_subtitles:
            start_time = subtitle['start']
            end_time = subtitle['end']
            text = subtitle['text']
            
            # 制約をチェック
            duration = end_time - start_time
            
            # 10秒制約をチェック
            if duration > 10.0:
                # 10秒に制限
                end_time = start_time + 10.0
                self.log_message(f'セグメントを10秒に制限: {start_time}-{end_time}秒', level='WARNING')
                duration = 10.0
            
            # 最小2.0秒の制約（人間が読める時間）
            if duration < 2.0:
                end_time = start_time + 2.0
                self.log_message(f'セグメントを2秒に延長: {start_time}-{end_time}秒', level='INFO')
            
            # 最終的な継続時間を再計算
            final_duration = end_time - start_time
            
            final_subtitle = {
                'start': start_time,
                'end': end_time,
                'text': text
            }
            
            final_subtitles.append(final_subtitle)
            self.log_message(f'字幕処理完了: {start_time}-{end_time}秒 ({final_duration:.1f}秒)')
        
        return final_subtitles
    
    def merge_short_segments_early(self, subtitles):
        """制約適用前の早期統合処理（最適化版）"""
        if len(subtitles) <= 1:
            return subtitles
        
        merged_subtitles = []
        i = 0
        
        while i < len(subtitles):
            current = subtitles[i]
            current_duration = current['end'] - current['start']
            
            # 統合対象判定（条件を緩和）
            should_try_merge = (
                current_duration < 2.0 or  # 短いセグメント
                (current_duration < 4.0 and len(current['text']) < 30)  # 短いテキスト
            )
            
            if should_try_merge and i + 1 < len(subtitles):
                next_segment = subtitles[i + 1]
                gap = next_segment['start'] - current['end']
                
                # 統合条件をチェック（緩和版）
                if self.should_merge_segments_optimized(current, next_segment, gap):
                    # セグメントを統合
                    merged = self.merge_two_segments(current, next_segment)
                    merged_subtitles.append(merged)
                    
                    # 統合ログ（詳細情報付き）
                    merged_duration = merged['end'] - merged['start']
                    self.log_message(
                        f'セグメント統合: {current["start"]:.1f}-{merged["end"]:.1f}秒 '
                        f'({merged_duration:.1f}秒) "{merged["text"][:40]}..."'
                    )
                    i += 2  # 2つのセグメントをスキップ
                    continue
            
            # 統合しない場合はそのまま追加
            merged_subtitles.append(current)
            i += 1
        
        return merged_subtitles
    
    def should_merge_segments_optimized(self, current, next_segment, gap):
        """最適化された統合条件判定"""
        # 基本条件
        time_proximity = gap <= 1.0  # 1.0秒以内に緩和
        combined_text = current['text'] + ' ' + next_segment['text']
        text_length_ok = len(combined_text) <= 150  # 150文字に拡大
        
        # 統合後の継続時間をチェック
        merged_duration = next_segment['end'] - current['start']
        duration_ok = merged_duration <= 10.0  # 10秒制約
        
        # デバッグログ
        if gap <= 1.0:  # 近接セグメントのみログ出力
            self.log_message(
                f'統合判定: gap={gap:.2f}s, text_len={len(combined_text)}, '
                f'duration={merged_duration:.1f}s -> '
                f'{"統合" if (time_proximity and text_length_ok and duration_ok) else "非統合"}'
            )
        
        return time_proximity and text_length_ok and duration_ok
    
    
    def merge_two_segments(self, current, next_segment):
        """2つのセグメントを統合"""
        # テキストを結合（改行を考慮した適切な区切り文字を使用）
        current_text = current['text'].rstrip()
        next_text = next_segment['text'].lstrip()
        
        # 改行で終わっている場合は、改行を保持して結合
        if current_text.endswith('\\n'):
            combined_text = current_text + next_text
        # 文末記号で終わっている場合は改行を挿入
        elif current_text.endswith(('。', '！', '？', '.', '!', '?')):
            combined_text = current_text + '\\n' + next_text
        # その他の場合はスペースを追加
        else:
            combined_text = current_text + ' ' + next_text
        
        return {
            'start': current['start'],
            'end': next_segment['end'],
            'text': combined_text
        }
    
    def delete_json_file(self, video_id):
        """JSONファイルの削除"""
        try:
            # 実行ファイルと同じディレクトリのjsonフォルダをチェック
            json_file = self.get_exe_dir() / "json" / f"{video_id}.json"
            
            if json_file.exists():
                json_file.unlink()  # ファイルを削除
                self.log_message(f'JSONファイルを削除しました: {video_id}')
                
                return jsonify({
                    'success': True,
                    'message': f'JSONファイルを削除しました: {video_id}.json'
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'JSONファイルが存在しません（既に削除済み）'
                })
                
        except Exception as e:
            self.log_message(f'JSONファイル削除エラー: {e}', level='ERROR')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    def read_json_file_direct(self, video_id):
        """ビデオIDにJSONファイルが存在する場合、その内容を直接読み取って返す"""
        try:
            # 実行ファイルと同じディレクトリのjsonフォルダをチェック
            json_file = self.get_exe_dir() / "json" / f"{video_id}.json"
            
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.log_message(f'JSONファイルを直接読み取り: {video_id}')
                
                return jsonify({
                    'success': True,
                    'subtitles': data.get('subtitles', []),
                    'title': data.get('title', ''),
                    'video_id': video_id,
                    'timestamp': data.get('timestamp', ''),
                    'from_file': True
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'JSONファイルが見つかりません'
                }), 404
                
        except json.JSONDecodeError as e:
            self.log_message(f'JSONファイル解析エラー: {e}', level='ERROR')
            return jsonify({
                'success': False,
                'error': 'JSONファイルの形式が不正です'
            }), 400
        except Exception as e:
            self.log_message(f'JSONファイル読み取りエラー: {e}', level='ERROR')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    

    def get_current_prompt(self):
        """現在使用するプロンプトを取得"""
        if self.use_custom_prompt and self.custom_prompt.strip():
            return self.custom_prompt
        return self.DEFAULT_PROMPT
    
    def reset_to_default_prompt(self):
        """プロンプトをデフォルトに戻す"""
        try:
            prompt_file = self.get_exe_dir() / "prompt.txt"
            if prompt_file.exists():
                prompt_file.unlink()  # ファイルを削除
                self.log_message("カスタムプロンプトファイルを削除しました")
            
            self.custom_prompt = ""
            self.use_custom_prompt = False
            self.log_message("プロンプトをデフォルトに戻しました")
        except Exception as e:
            self.log_message(f"プロンプトリセットエラー: {e}", level='ERROR')
    
    def save_custom_prompt(self, prompt_text):
        """カスタムプロンプトをファイルに保存"""
        try:
            prompt_file = self.get_exe_dir() / "prompt.txt"
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt_text.strip())
            
            self.custom_prompt = prompt_text.strip()
            self.use_custom_prompt = True
            self.log_message("カスタムプロンプトをファイルに保存しました")
        except Exception as e:
            self.log_message(f"カスタムプロンプト保存エラー: {e}", level='ERROR')
            raise
    
    def load_custom_prompt_from_file(self):
        """カスタムプロンプトをファイルから読み込み"""
        try:
            prompt_file = self.get_exe_dir() / "prompt.txt"
            if prompt_file.exists():
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_content = f.read().strip()
                
                if prompt_content:
                    self.custom_prompt = prompt_content
                    self.use_custom_prompt = True
                    self.log_message("カスタムプロンプトをファイルから読み込みました")
                    return True
            
            # ファイルが存在しないか空の場合
            self.custom_prompt = ""
            self.use_custom_prompt = False
            return False
            
        except Exception as e:
            self.log_message(f"カスタムプロンプト読み込みエラー: {e}", level='ERROR')
            self.custom_prompt = ""
            self.use_custom_prompt = False
            return False
    
    def get_prompt_status(self):
        """現在のプロンプト設定状況を取得"""
        if self.use_custom_prompt and self.custom_prompt.strip():
            return "カスタムプロンプト使用中"
        return "デフォルトプロンプト使用中"
    
    def reset_prompt_to_default(self):
        """プロンプトをデフォルトに戻す（GUI操作）"""
        # ファイルとメモリ上の変数をリセット
        self.reset_to_default_prompt()
        
        # GUIを更新
        if hasattr(self, 'prompt_text'):
            self.prompt_text.delete('1.0', tk.END)
            self.prompt_text.insert('1.0', self.DEFAULT_PROMPT)
        
        # 全ステータス表示を更新
        self.update_prompt_status_displays()
        
        messagebox.showinfo("プロンプト設定", "プロンプトをデフォルトに戻しました")
    
    def save_custom_prompt_from_gui(self):
        """GUIからカスタムプロンプトを保存"""
        if hasattr(self, 'prompt_text'):
            prompt_text = self.prompt_text.get('1.0', tk.END).strip()
            
            if not prompt_text:
                messagebox.showwarning("プロンプト設定", "プロンプトが空です")
                return
            
            # ファイルとメモリ上の変数に保存
            self.save_custom_prompt(prompt_text)
            
            # 全ステータス表示を更新
            self.update_prompt_status_displays()
            
            messagebox.showinfo("プロンプト設定", "カスタムプロンプトを保存しました")
    
    def clear_log(self):
        """ログをクリア"""
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete('1.0', tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.log_message("ログをクリアしました")
    
    def update_prompt_status_displays(self):
        """全てのプロンプトステータス表示を更新"""
        status_text = self.get_prompt_status()
        if hasattr(self, 'prompt_status_basic'):
            self.prompt_status_basic.config(text=status_text)
    
    def initialize_prompt_display(self):
        """プロンプト表示エリアの初期化"""
        try:
            if hasattr(self, 'prompt_text') and self.prompt_text.winfo_exists():
                self.prompt_text.delete('1.0', tk.END)
                if self.use_custom_prompt and self.custom_prompt.strip():
                    self.prompt_text.insert('1.0', self.custom_prompt)
                else:
                    self.prompt_text.insert('1.0', self.DEFAULT_PROMPT)
            
            # 全ステータス表示を更新
            self.update_prompt_status_displays()
        except Exception as e:
            self.log_message(f"プロンプト表示初期化エラー: {e}", level='ERROR')

    def set_app_icon(self):
        """アプリケーションアイコンを設定"""
        try:
            # アイコンファイルのパスを取得
            icon_paths = [
                # translation-serverフォルダ内のiconsフォルダ
                "icons/icons-48.png",
                # PyInstaller実行ファイル用パス（バンドル後）
                "icons/icons-48.png",
                # 同一ディレクトリ用パス  
                "icons-48.png"
            ]
            
            icon_set = False
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        # tkinterのphotoimage形式でアイコンを設定
                        icon_image = tk.PhotoImage(file=icon_path)
                        self.root.iconphoto(True, icon_image)
                        self.log_message(f"アイコンを設定しました: {icon_path}")
                        icon_set = True
                        break
                    except Exception as e:
                        self.log_message(f"アイコン設定失敗 {icon_path}: {e}")
                        continue
                        
            if not icon_set:
                self.log_message("アイコンファイルが見つかりません", level='WARNING')
                
        except Exception as e:
            self.log_message(f"アイコン設定エラー: {e}", level='ERROR')

    def setup_gui(self):
        """GUI初期化（タブ構造）"""
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("700x550")
        self.root.resizable(True, True)
        
        # アイコン設定
        self.set_app_icon()
        
        # ウィンドウを閉じる時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タブ作成
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # タブ1: 基本設定
        self.setup_basic_settings_tab()
        
        # タブ2: ログ・ステータス
        self.setup_log_status_tab()
        
        # グリッド設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
    
    def setup_basic_settings_tab(self):
        """基本設定タブの設定"""
        basic_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(basic_frame, text="基本設定")
        
        # APIキー設定エリア
        api_frame = ttk.LabelFrame(basic_frame, text="API設定", padding="10")
        api_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        api_frame.columnconfigure(1, weight=1)
        
        # APIキー入力
        ttk.Label(api_frame, text="API：").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=50, show="*")
        api_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 5), pady=5)
        
        # APIキー取得ボタン
        ttk.Button(api_frame, text="APIキーを取得", 
                  command=self.open_api_key_url).grid(row=0, column=2, padx=(5, 0), pady=5)
        
        # 保存ボタン
        ttk.Button(api_frame, text="設定を保存", 
                  command=self.save_settings).grid(row=0, column=3, padx=(10, 0), pady=5)
        
        # 横並びエリア: 起動設定 + サーバー操作
        middle_frame = ttk.Frame(basic_frame)
        middle_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        middle_frame.columnconfigure(0, weight=1)
        middle_frame.columnconfigure(1, weight=1)
        
        # 自動起動設定エリア（左側）
        startup_frame = ttk.LabelFrame(middle_frame, text="起動設定", padding="2")
        startup_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        startup_frame.configure(height=60)
        startup_frame.grid_propagate(False)
        
        self.auto_start_var = tk.BooleanVar()
        ttk.Checkbutton(startup_frame, text="Windows起動時に自動起動", 
                       variable=self.auto_start_var, 
                       command=self.toggle_auto_start).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # サーバー操作エリア（右側）
        server_frame = ttk.LabelFrame(middle_frame, text="サーバー操作", padding="2")
        server_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        server_frame.configure(height=60)
        server_frame.grid_propagate(False)
        
        # 全要素を横並び配置
        server_content = ttk.Frame(server_frame)
        server_content.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # ポート番号設定
        ttk.Label(server_content, text="ポート:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value=str(SERVER_PORT))
        port_entry = ttk.Entry(server_content, textvariable=self.port_var, width=8)
        port_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        # サーバー操作ボタン
        self.start_button = ttk.Button(server_content, text="サーバー開始", command=self.start_server)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button = ttk.Button(server_content, text="サーバー停止", command=self.stop_server, state="disabled")
        self.stop_button.pack(side=tk.LEFT)
        
        # プロンプト設定エリア（下部）
        prompt_frame = ttk.LabelFrame(basic_frame, text="プロンプト設定", padding="10")
        prompt_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(1, weight=1)
        
        # プロンプトステータス表示
        prompt_status_container = ttk.Frame(prompt_frame)
        prompt_status_container.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(prompt_status_container, text="現在の設定:").pack(side=tk.LEFT)
        self.prompt_status_basic = ttk.Label(prompt_status_container, text="デフォルトプロンプト使用中")
        self.prompt_status_basic.pack(side=tk.LEFT, padx=(5, 0))
        
        # プロンプト編集エリア
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, width=80, height=12, wrap=tk.NONE)
        self.prompt_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # プロンプト操作ボタン
        prompt_button_frame = ttk.Frame(prompt_frame)
        prompt_button_frame.grid(row=2, column=0, sticky=tk.W)
        
        ttk.Button(prompt_button_frame, text="デフォルトに戻す", 
                  command=self.reset_prompt_to_default).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(prompt_button_frame, text="カスタムプロンプトを保存", 
                  command=self.save_custom_prompt_from_gui).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(prompt_button_frame, text="設定を保存", 
                  command=self.save_settings).pack(side=tk.LEFT)
        
        # グリッド設定
        basic_frame.columnconfigure(0, weight=1)
        basic_frame.columnconfigure(1, weight=1)
        basic_frame.rowconfigure(2, weight=1)
    
    def setup_log_status_tab(self):
        """ログタブの設定"""
        log_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(log_frame, text="ログ")
        
        # ログ表示エリア
        log_display_frame = ttk.LabelFrame(log_frame, text="ログ", padding="10")
        log_display_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_display_frame.columnconfigure(0, weight=1)
        log_display_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_display_frame, width=80, height=25, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ログ操作ボタン
        log_button_frame = ttk.Frame(log_display_frame)
        log_button_frame.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        ttk.Button(log_button_frame, text="ログをクリア", 
                  command=self.clear_log).pack(side=tk.LEFT)
        
        # グリッド設定
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def setup_system_tray(self):
        """システムトレイ初期化"""
        # アイコン画像を作成
        image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        draw = ImageDraw.Draw(image)
        draw.text((10, 25), "YT", fill=(255, 255, 255))
        
        # トレイメニュー
        menu = pystray.Menu(
            pystray.MenuItem("設定を開く", self.show_window),
            pystray.MenuItem("サーバー開始", self.start_server),
            pystray.MenuItem("サーバー停止", self.stop_server),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", self.quit_application)
        )
        
        self.tray_icon = pystray.Icon("youtube_translator", image, APP_NAME, menu)
    
    def log_message(self, message, level='INFO'):
        """ログメッセージを表示"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        # コンソールログ
        if level == 'ERROR':
            logger.error(message)
        else:
            logger.info(message)
        
        # GUIログ
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
    
    def start_server(self):
        """HTTPサーバー開始"""
        if self.server_running:
            return
            
        # APIキーチェック
        if not self.api_key:
            self.api_key = self.api_key_var.get()
            if not self.api_key:
                messagebox.showwarning("APIキー未設定", "APIキーを設定してから開始してください")
                return
        
        # ポート番号取得
        try:
            port = int(self.port_var.get()) if hasattr(self, 'port_var') else SERVER_PORT
            if not (1024 <= port <= 65535):
                raise ValueError("ポート番号は1024-65535の範囲で設定してください")
        except ValueError as e:
            messagebox.showerror("ポート設定エラー", str(e))
            return
        
        def run_server():
            try:
                self.server_running = True
                self.log_message(f"サーバー開始: http://localhost:{port}")
                self.app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
            except Exception as e:
                self.log_message(f"サーバーエラー: {e}", level='ERROR')
                self.server_running = False
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # GUI更新
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
    
    def stop_server(self):
        """HTTPサーバー停止"""
        self.server_running = False
        self.log_message("サーバー停止")
        
        # GUI更新
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
    
    def save_settings(self, update_api_key=True):
        """設定保存（暗号化されたファイルに保存）"""
        if update_api_key:
            self.api_key = self.api_key_var.get()
        
        # 設定を暗号化してファイルに保存
        try:
            settings = {
                "api_key": self.api_key,
                "auto_start": self.auto_start_var.get()
            }
            
            if self.security_manager.save_settings(settings):
                self.log_message("設定を暗号化して保存しました")
                if update_api_key:  # APIキー保存時のみメッセージ表示
                    messagebox.showinfo("設定保存", "設定が暗号化されて保存されました")
            else:
                raise Exception("暗号化ファイルの保存に失敗しました")
                
        except Exception as e:
            self.log_message(f"設定保存エラー: {e}", level='ERROR')
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")
    
    def open_api_key_url(self):
        """APIキー取得ページをブラウザで開く"""
        try:
            webbrowser.open("https://aistudio.google.com/app/apikey")
            self.log_message("APIキー取得ページを開きました")
        except Exception as e:
            self.log_message(f"ブラウザ起動エラー: {e}", level='ERROR')
            messagebox.showerror("エラー", f"ブラウザの起動に失敗しました: {e}")
    
    def load_settings(self):
        """設定読み込み（暗号化ファイルから）"""
        try:
            # 暗号化されたファイルから設定を読み込み
            settings = self.security_manager.load_settings()
            
            # 設定が取得できた場合は適用
            if settings:
                self.api_key = settings.get("api_key", "")
                self.auto_start = settings.get("auto_start", False)
                
                # GUI要素に反映
                if hasattr(self, 'api_key_var'):
                    self.api_key_var.set(self.api_key)
                if hasattr(self, 'auto_start_var'):
                    self.auto_start_var.set(self.auto_start)
                
                self.log_message("設定を暗号化ファイルから読み込みました")
            else:
                self.log_message("設定ファイルが見つかりません（初回起動）")
            
        except Exception as e:
            self.log_message(f"設定読み込みエラー: {e}", level='ERROR')
            # エラーが発生した場合はデフォルト値を使用
            self.api_key = ""
            self.auto_start = False
    
    def toggle_auto_start(self):
        """自動起動設定の切り替え"""
        auto_start = self.auto_start_var.get()
        exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                if auto_start:
                    winreg.SetValueEx(key, "YouTubeTranslator", 0, winreg.REG_SZ, exe_path)
                    self.log_message("自動起動を有効にしました")
                else:
                    try:
                        winreg.DeleteValue(key, "YouTubeTranslator")
                        self.log_message("自動起動を無効にしました")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            self.log_message(f"自動起動設定エラー: {e}", level='ERROR')
    
    def show_window(self, icon=None, item=None):
        """ウィンドウを表示"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def hide_window(self):
        """ウィンドウを隠す"""
        self.root.withdraw()
    
    def on_closing(self):
        """ウィンドウを閉じる時の処理"""
        self.hide_window()
    
    def quit_application(self, icon=None, item=None):
        """アプリケーション終了"""
        self.stop_server()
        self.tray_icon.stop()
        self.root.quit()
        sys.exit(0)
    
    def run(self):
        """アプリケーション実行"""
        # トレイアイコンを別スレッドで起動
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
        # 初期ログ
        self.log_message(f"{APP_NAME} v{APP_VERSION} 起動")
        self.log_message("設定画面が表示されました")
        self.log_message("タスクトレイにアイコンが追加されました")
        
        # 自動でサーバー開始
        if self.api_key:
            self.root.after(1000, self.start_server)
        
        # GUI開始
        self.root.mainloop()

def check_single_instance():
    """アプリケーションの多重起動をチェック"""
    # ユニークな名前のミューテックスを作成
    mutex_name = "Global\\YouTubeAITranslation_Mutex_8888"
    
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
        print(f"エラーが発生しました: {e}")
        sys.exit(1)
    finally:
        # ミューテックスを解放
        if mutex and mutex is not False:
            win32api.CloseHandle(mutex)

if __name__ == '__main__':
    main()