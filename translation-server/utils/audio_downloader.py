"""
音声ダウンロード：yt-dlpを使用したYouTube音声の取得
"""

import os
import time
import logging
from pathlib import Path
import yt_dlp
import shutil

logger = logging.getLogger(__name__)


class AudioDownloader:
    """YouTube音声ダウンロード管理クラス"""
    
    def __init__(self, temp_dir):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
    
    def download_audio(self, video_id, progress_callback=None):
        """
        YouTube動画の音声をダウンロード
        
        Args:
            video_id: YouTube動画ID
            progress_callback: 進捗更新用のコールバック関数
            
        Returns:
            tuple: (成功フラグ, 結果辞書またはエラーメッセージ)
                   成功時の結果辞書: {'path': str, 'title': str}
        """
        audio_path = self.temp_dir / f"{video_id}.mp3"
        
        # キャッシュチェック
        if audio_path.exists():
            logger.info(f"キャッシュされた音声ファイルを使用: {audio_path}")
            return True, {'path': str(audio_path), 'title': 'Cached Audio'}
        
        # ffmpegがインストールされているか確認
        ffmpeg_available = shutil.which('ffmpeg') is not None
        
        # yt-dlpオプション
        ydl_opts = {
            'format': 'bestaudio[abr<=128]/bestaudio/best',
            'outtmpl': str(audio_path.with_suffix('.%(ext)s')),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        # ffmpegが利用可能な場合のみ音声変換を有効化
        if ffmpeg_available:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }]
            logger.info("ffmpegが利用可能です。MP3形式で音声を抽出します。")
        else:
            logger.warning("ffmpegが見つかりません。音声ファイルは元の形式のままダウンロードされます。")
            logger.warning("MP3形式での抽出を行うには、ffmpegをインストールしてください。")
        
        # 進捗コールバックの設定
        if progress_callback:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d:
                        percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                        progress_callback(int(percent))
                    elif 'total_bytes_estimate' in d:
                        percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                        progress_callback(int(percent))
            
            ydl_opts['progress_hooks'] = [progress_hook]
        
        try:
            start_time = time.time()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"音声ダウンロード開始: {video_id}")
                info_dict = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
                
                # ダウンロード完了確認
                if not audio_path.exists():
                    # 拡張子違いのファイルを探す
                    for ext in ['.mp3', '.m4a', '.webm', '.opus', '.wav']:
                        alt_path = audio_path.with_suffix(ext)
                        if alt_path.exists():
                            audio_path = alt_path
                            break
                    
                    # まだ見つからない場合は、ディレクトリ内のファイルを確認
                    if not audio_path.exists():
                        for file in self.temp_dir.glob(f"{video_id}.*"):
                            if file.suffix in ['.mp3', '.m4a', '.webm', '.opus', '.wav']:
                                audio_path = file
                                break
                
                download_time = time.time() - start_time
                logger.info(f"音声ダウンロード完了: {download_time:.1f}秒")
                
                # 動画タイトルを取得
                video_title = info_dict.get('title', 'Unknown')
                
                return True, {'path': str(audio_path), 'title': video_title}
                
        except Exception as e:
            error_msg = f"音声ダウンロードエラー: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def cleanup_old_files(self, max_age_hours=24):
        """古い一時ファイルを削除"""
        try:
            current_time = time.time()
            for file_path in self.temp_dir.glob("*"):
                if file_path.suffix in ['.mp3', '.m4a', '.webm', '.opus', '.wav']:
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_hours * 3600:
                        file_path.unlink()
                        logger.info(f"古い音声ファイルを削除: {file_path}")
        except Exception as e:
            logger.error(f"クリーンアップエラー: {e}")