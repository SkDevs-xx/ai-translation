# YouTube AI Translation Server

Chrome拡張機能と連携してYouTube動画の音声を高速ダウンロード・翻訳するサーバーアプリケーション

## 使い方

### 開発時の実行

```batch
# 仮想環境をアクティベート
venv\Scripts\activate.bat

# アプリケーションを実行
python youtube-ai-translation.py
```

### 実行ファイル（exe）のビルド

```batch
# 仮想環境を自動セットアップしてビルド
build_exe.bat
```

ビルドされたexeファイルは `dist/youtube-ai-translation.exe` に作成されます。

## 必要な環境

- Python 3.8以上
- Windows OS（自動起動機能のため）
- Google Gemini API キー

## ファイル構成

```
translation-server/
├── youtube-ai-translation.py     # メインエントリーポイント
├── setup_dev.bat                # 開発環境セットアップ
├── run.bat                      # アプリケーション実行
├── build_exe.bat                # exe ビルド
├── requirements.txt             # Python 依存関係
├── icons/                       # アイコンファイル
├── core/                        # コア機能モジュール
├── server/                      # サーバー関連モジュール
├── translation/                 # 翻訳処理モジュール
├── gui/                         # GUI モジュール
└── utils/                       # ユーティリティモジュール
```

## 初回起動時の設定

1. アプリケーションを起動
2. 「基本設定」タブでGoogle Gemini APIキーを入力
3. 必要に応じて「Windows起動時に自動的に開始」を有効化
4. 「ログ・ステータス」タブでサーバーを起動

## トラブルシューティング

### 仮想環境が作成できない
- Python がインストールされているか確認
- `python --version` でバージョンを確認

### 依存関係のインストールに失敗する
- インターネット接続を確認
- 企業プロキシ環境の場合は、プロキシ設定が必要

### exe ファイルが起動しない
- Windows Defender やアンチウイルスソフトの除外設定を確認
- `icons/` フォルダが同じディレクトリにあるか確認