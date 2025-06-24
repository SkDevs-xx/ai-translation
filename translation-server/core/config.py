"""
設定定数とデフォルト値の管理
"""

# アプリケーション設定
APP_NAME = "YouTube AI Translation"
APP_VERSION = "2.0.0"
SERVER_PORT = 8888

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
- Use `\\n` to break a line.
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
"text": "こんにちは皆さん。\\n今日は素晴らしい日ですね。"
},
{
"start": "0:30",
"text": "はい、承知いたしました。\\n詳しくご説明します。"
},
{
"start": "12:05",
"text": "これは非常に重要なポイントです。\\n皆さんに覚えておいてほしいことがあります。"
}
]

"""

# ディレクトリ設定
TEMP_DIR = "temp"
JSON_DIR = "json"

# API設定
GEMINI_MODEL_NAME = "gemini-2.0-flash-exp"
API_TIMEOUT = 120  # 秒
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

# 字幕処理設定
MIN_SEGMENT_DURATION = 2.0  # 最小セグメント長（秒）
MAX_SEGMENT_DURATION = 10.0  # 最大セグメント長（秒）
MERGE_GAP_THRESHOLD = 1.0    # 統合判定の時間間隔閾値（秒）
MIN_TEXT_LENGTH_FOR_DURATION = 10  # 短すぎるテキストの判定文字数