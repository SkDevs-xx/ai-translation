"""
字幕処理：セグメント統合、時間調整、フォーマット処理
"""

import re
import logging
from core.config import MIN_SEGMENT_DURATION, MAX_SEGMENT_DURATION, MERGE_GAP_THRESHOLD, MIN_TEXT_LENGTH_FOR_DURATION

logger = logging.getLogger(__name__)


def convert_mmss_to_seconds(time_str):
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
        logger.error(f'時間形式エラー: {time_str}')
        return 0.0


def should_merge_segments(current, next_segment, gap_threshold=MERGE_GAP_THRESHOLD):
    """2つのセグメントを統合すべきか判定"""
    # 時間的な近さをチェック
    gap = next_segment['start'] - current['end']
    time_proximity = gap <= gap_threshold
    
    # テキストの長さをチェック（短すぎるテキストは統合候補）
    current_text = current['text'].strip()
    text_length_ok = len(current_text) < MIN_TEXT_LENGTH_FOR_DURATION
    
    # 統合後の長さが制限内かチェック
    combined_duration = next_segment['end'] - current['start']
    duration_ok = combined_duration <= MAX_SEGMENT_DURATION
    
    logger.info(
        f'統合判定: gap={gap:.2f}s, text_len={len(current_text)}, '
        f'duration={combined_duration:.1f}s -> {"統合" if (time_proximity and text_length_ok and duration_ok) else "非統合"}'
    )
    
    return time_proximity and text_length_ok and duration_ok


def merge_two_segments(current, next_segment):
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


def process_subtitles_with_end_times(raw_subtitles):
    """字幕データにend時間を追加し、統合・制約を適用"""
    if not raw_subtitles:
        return []
    
    # mm:ss形式をまず秒数に変換
    for subtitle in raw_subtitles:
        if 'start' in subtitle:
            subtitle['start'] = convert_mmss_to_seconds(subtitle['start'])
        if 'end' in subtitle:
            subtitle['end'] = convert_mmss_to_seconds(subtitle['end'])
    
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
            # 次のセグメントのstart時間をendとして使用
            if i < len(raw_subtitles) - 1:
                next_start = raw_subtitles[i + 1].get('start', start_time + 2)
                end_time = next_start - 0.1  # 0.1秒のギャップ
            else:
                # 最後のセグメントは3秒のデフォルト
                end_time = start_time + 3.0
        
        basic_subtitles.append({
            'start': start_time,
            'end': end_time,
            'text': text
        })
    
    # Step 2: 短いセグメントの統合
    merged_subtitles = []
    i = 0
    while i < len(basic_subtitles):
        current = basic_subtitles[i]
        
        # 次のセグメントとの統合を検討
        if i < len(basic_subtitles) - 1:
            next_segment = basic_subtitles[i + 1]
            
            if should_merge_segments(current, next_segment):
                # セグメントを統合
                merged = merge_two_segments(current, next_segment)
                logger.info(
                    f'セグメント統合: {current["start"]:.1f}-{next_segment["end"]:.1f}秒 '
                    f'({merged["end"] - merged["start"]:.1f}秒) "{merged["text"][:30]}..."'
                )
                # 統合されたセグメントを現在のセグメントとして更新
                basic_subtitles[i] = merged
                # 次のセグメントを削除
                basic_subtitles.pop(i + 1)
                # iは増やさない（統合後のセグメントをさらに次と比較）
                continue
        
        merged_subtitles.append(current)
        i += 1
    
    # Step 3: 時間制約の適用
    final_subtitles = []
    for subtitle in merged_subtitles:
        start_time = subtitle['start']
        end_time = subtitle['end']
        duration = end_time - start_time
        
        # 最小持続時間の確保
        if duration < MIN_SEGMENT_DURATION:
            end_time = start_time + MIN_SEGMENT_DURATION
            logger.info(f'セグメントを{MIN_SEGMENT_DURATION}秒に延長: {start_time:.1f}-{end_time:.1f}秒')
        
        # 最大持続時間の制限
        if duration > MAX_SEGMENT_DURATION:
            end_time = start_time + MAX_SEGMENT_DURATION
            logger.warning(f'セグメントを{MAX_SEGMENT_DURATION}秒に制限: {start_time:.1f}-{end_time:.1f}秒')
        
        final_subtitles.append({
            'start': start_time,
            'end': end_time,
            'text': subtitle['text']
        })
        
        logger.info(f'字幕処理完了: {start_time:.1f}-{end_time:.1f}秒 ({end_time - start_time:.1f}秒)')
    
    return final_subtitles