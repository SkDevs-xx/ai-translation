"""
Flask サーバーの初期化とCORS設定
"""

from flask import Flask, request, jsonify
from flask_cors import CORS


def create_app():
    """Flaskアプリケーションを作成して設定"""
    app = Flask(__name__)
    
    # CORS設定 - Chrome拡張機能との通信を確実にするため
    CORS(app, 
         origins=[
             "https://www.youtube.com",
             "https://youtube.com", 
             "chrome-extension://*"
         ],
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "DELETE", "OPTIONS"],
         supports_credentials=True
    )
    
    # 追加のCORSヘッダー設定とデバッグログ
    @app.after_request
    def after_request(response):
        import logging
        logger = logging.getLogger(__name__)
        
        # Chrome拡張機能からのアクセスを明示的に許可
        origin = request.headers.get('Origin')
        user_agent = request.headers.get('User-Agent', '')
        
        # リクエスト詳細をログ出力
        logger.info(f"Request: {request.method} {request.path} - Origin: {origin} - Status: {response.status_code}")
        
        if origin and (origin.startswith('chrome-extension://') or 
                      'youtube.com' in origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            logger.info(f"CORS headers added for origin: {origin}")
        
        return response
    
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
    
    @app.route('/test/chrome-extension', methods=['GET'])
    def test_chrome_extension():
        return handlers.handle_test_chrome_extension()
    
    # エラーハンドラー
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'API endpoint not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    
    @app.errorhandler(TimeoutError)
    def timeout_error(error):
        return jsonify({
            'success': False,
            'error': 'Request timeout - translation process took too long'
        }), 408