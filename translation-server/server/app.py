"""
Flask サーバーの初期化とCORS設定
"""

from flask import Flask
from flask_cors import CORS


def create_app():
    """Flaskアプリケーションを作成して設定"""
    app = Flask(__name__)
    
    # CORS設定
    CORS(app, origins=[
        "https://www.youtube.com",
        "https://youtube.com",
        "chrome-extension://*"
    ])
    
    return app


def setup_routes(app, handlers):
    """APIルートを設定"""
    
    @app.route('/download/<video_id>', methods=['GET'])
    def download(video_id):
        return handlers.handle_download(video_id)
    
    @app.route('/delete_json/<video_id>', methods=['DELETE'])
    def delete_json(video_id):
        return handlers.handle_delete_json(video_id)
    
    @app.route('/read_json/<video_id>', methods=['GET'])
    def read_json(video_id):
        return handlers.handle_read_json(video_id)
    
    @app.route('/health', methods=['GET'])
    def health():
        return handlers.handle_health()