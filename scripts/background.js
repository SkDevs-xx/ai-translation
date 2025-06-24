// background.js - 完全再設計・シンプル版

const LOCAL_SERVER_URL = 'http://localhost:8888';

// メッセージ処理 - 最小限
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'translate') {
        handleTranslation(message.videoId, sendResponse);
        return true; // 非同期レスポンス
    }
    
    if (message.type === 'get_status') {
        getTranslationStatus(message.videoId, sendResponse);
        return true;
    }
    
    if (message.type === 'delete_translation') {
        deleteTranslation(message.videoId, sendResponse);
        return true;
    }
    
    if (message.type === 'check_server_status') {
        checkServerHealth(sendResponse);
        return true;
    }
});

// 翻訳処理 - 超シンプル
async function handleTranslation(videoId, sendResponse) {
    try {
        console.log(`[BG] Translation request for: ${videoId}`);
        
        // 1. キャッシュチェック
        const cached = await getCachedTranslation(videoId);
        if (cached) {
            console.log(`[BG] Using cached data`);
            sendResponse({ success: true, data: cached });
            return;
        }
        
        // 2. サーバーから取得
        console.log(`[BG] Fetching from server`);
        const response = await fetch(`${LOCAL_SERVER_URL}/download/${videoId}`, {
            method: 'GET',
            signal: AbortSignal.timeout(300000)
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.subtitles) {
            // 3. キャッシュに保存（非同期・ノンブロッキング）
            saveToCache(videoId, data).catch(console.error);
            
            console.log(`[BG] Translation completed`);
            sendResponse({ success: true, data: data });
        } else {
            throw new Error(data.error || 'Invalid response from server');
        }
        
    } catch (error) {
        console.error(`[BG] Translation error:`, error);
        let errorMessage = error.message;
        
        if (error.name === 'AbortError') {
            errorMessage = 'サーバーがタイムアウトしました';
        } else if (errorMessage.includes('Failed to fetch')) {
            errorMessage = 'ローカルサーバーに接続できません';
        }
        
        sendResponse({ success: false, error: errorMessage });
    }
}

// キャッシュ取得 - シンプル
async function getCachedTranslation(videoId) {
    try {
        const result = await chrome.storage.local.get(videoId);
        return result[videoId] || null;
    } catch (error) {
        console.error(`[BG] Cache read error:`, error);
        return null;
    }
}

// キャッシュ保存 - 非同期・エラー時も継続
async function saveToCache(videoId, data) {
    try {
        await chrome.storage.local.set({ [videoId]: data });
        console.log(`[BG] Cached: ${videoId}`);
    } catch (error) {
        console.error(`[BG] Cache save error:`, error);
        // エラーでも処理は継続
    }
}

// ステータス取得
async function getTranslationStatus(videoId, sendResponse) {
    const cached = await getCachedTranslation(videoId);
    if (cached && cached.subtitles) {
        sendResponse({ success: true, data: cached });
    } else {
        sendResponse({ success: false });
    }
}

// 削除処理
async function deleteTranslation(videoId, sendResponse) {
    try {
        // ローカルキャッシュ削除
        await chrome.storage.local.remove(videoId);
        
        // サーバー側削除（失敗しても無視）
        try {
            await fetch(`${LOCAL_SERVER_URL}/delete_json/${videoId}`, { method: 'DELETE' });
        } catch (serverError) {
            console.warn(`[BG] Server delete failed (ignored):`, serverError);
        }
        
        sendResponse({ success: true });
    } catch (error) {
        console.error(`[BG] Delete error:`, error);
        sendResponse({ success: false, error: error.message });
    }
}

// サーバー状態確認
async function checkServerHealth(sendResponse) {
    try {
        const response = await fetch(`${LOCAL_SERVER_URL}/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(3000)
        });
        
        if (response.ok) {
            sendResponse({ success: true, message: 'AI翻訳サーバー起動中' });
        } else {
            sendResponse({ success: false, error: 'サーバーエラー' });
        }
    } catch (error) {
        sendResponse({ success: false, error: 'サーバー未起動' });
    }
}