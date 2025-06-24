// content.js - 完全再設計・超軽量版

// === グローバル変数（最小限） ===
let subtitlesData = null;
let isSubtitleEnabled = false;
let subtitleElement = null;
let currentVideoId = null;
let lastUrl = location.href;

// ユーザー設定（オプション画面で調整可能）
let userSettings = {
  fontSizeRem: 1.5,
  bgColor: '#000000',
  bgOpacity: 0.75
};

// 自動調整設定（コードで固定）
const AUTO_SETTINGS = {
  paddingHorizontal: 8,
  paddingVertical: 8,
  borderRadius: 8,
  baseWidth: 1200,
  maxWidth: 1800,
  autoWidthEnabled: true
};

// === 設定の読み込み ===
chrome.storage.local.get(userSettings, (settings) => {
  userSettings = { ...userSettings, ...settings };
});

// 設定変更の監視
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace !== 'local') return;

  for (let key in changes) {
    if (userSettings.hasOwnProperty(key)) {
      userSettings[key] = changes[key].newValue;
      applyStyles();
    }
  }
});

// === スタイル関数 ===
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : null;
}

function applyStyles() {
  if (!subtitleElement) return;

  const rgb = hexToRgb(userSettings.bgColor);
  if (rgb) {
    subtitleElement.style.backgroundColor = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${userSettings.bgOpacity})`;
  }
  subtitleElement.style.fontSize = `${userSettings.fontSizeRem}rem`;
  subtitleElement.style.padding = `${AUTO_SETTINGS.paddingVertical}px ${AUTO_SETTINGS.paddingHorizontal}px`;
  subtitleElement.style.borderRadius = `${AUTO_SETTINGS.borderRadius}px`;

  // 横幅は動的調整で設定されるため、ここでは設定しない
}

// === 初期化（シンプル） ===
function init() {
  currentVideoId = getVideoId();
  if (!currentVideoId) return;

  // CSS アニメーションを追加（一度だけ）
  if (!document.getElementById('ai-translate-styles')) {
    const style = document.createElement('style');
    style.id = 'ai-translate-styles';
    style.textContent = `
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `;
    document.head.appendChild(style);
  }

  // 既存のボタンを削除
  const existingButton = document.querySelector('.ai-translate-button-container');
  if (existingButton) existingButton.remove();

  // 字幕要素を削除
  if (subtitleElement) {
    subtitleElement.remove();
    subtitleElement = null;
  }

  // 状態をリセット
  subtitlesData = null;
  isSubtitleEnabled = false;

  // ボタンを追加
  addTranslateButton();

  // 既存の翻訳があるかチェック
  checkExistingTranslation();
}

// === ボタン関連 ===
function addTranslateButton() {
  const targetElement = document.querySelector("#actions.ytd-watch-metadata");
  if (!targetElement) {
    setTimeout(addTranslateButton, 1000); // 1秒後にリトライ
    return;
  }

  const container = document.createElement('div');
  container.className = 'ai-translate-button-container';
  container.style.cssText = `
    display: flex;
    align-items: center;
    margin-right: 8px;
    order: -1;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 18px;
    overflow: hidden;
    height: 36px;
  `;

  // AI翻訳ボタン
  const translateButton = document.createElement('button');
  translateButton.id = 'ai-translate-button';
  translateButton.innerHTML = `
    <span style="font-size: 16px; margin-right: 4px;">🌐</span>
    <span>AI翻訳</span>
  `;
  translateButton.style.cssText = `
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 0 16px;
    height: 36px;
    background: transparent;
    color: rgba(255, 255, 255, 0.88);
    border: none;
    border-radius: 0;
    border-top-left-radius: 18px;
    border-bottom-left-radius: 18px;
    font-family: "YouTube Noto", Roboto, Arial, sans-serif;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.1s cubic-bezier(0.05, 0, 0, 1);
    white-space: nowrap;
    text-align: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
  `;

  // ホバー効果を追加
  translateButton.addEventListener('mouseenter', () => {
    if (!translateButton.disabled) {
      translateButton.style.background = 'rgba(255, 255, 255, 0.1)';
      translateButton.style.color = 'rgba(255, 255, 255, 1)';
    }
  });

  translateButton.addEventListener('mouseleave', () => {
    if (!translateButton.disabled) {
      translateButton.style.background = 'transparent';
      translateButton.style.color = 'rgba(255, 255, 255, 0.88)';
    }
  });

  // 削除ボタン
  const deleteButton = document.createElement('button');
  deleteButton.id = 'ai-delete-button';
  deleteButton.innerHTML = `
    <span style="font-size: 16px; margin-right: 4px;">🗑️</span>
    <span>削除</span>
  `;
  deleteButton.style.cssText = `
    display: none;
    align-items: center;
    gap: 8px;
    padding: 0 16px;
    height: 36px;
    background: transparent;
    color: rgba(255, 255, 255, 0.88);
    border: none;
    border-radius: 0;
    border-top-right-radius: 18px;
    border-bottom-right-radius: 18px;
    border-left: 1px solid rgba(255, 255, 255, 0.2);
    font-family: "YouTube Noto", Roboto, Arial, sans-serif;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.1s cubic-bezier(0.05, 0, 0, 1);
    white-space: nowrap;
    text-align: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
  `;

  // 削除ボタンのホバー効果
  deleteButton.addEventListener('mouseenter', () => {
    if (!deleteButton.disabled) {
      deleteButton.style.background = 'rgba(255, 255, 255, 0.1)';
      deleteButton.style.color = 'rgba(255, 255, 255, 1)';
    }
  });

  deleteButton.addEventListener('mouseleave', () => {
    if (!deleteButton.disabled) {
      deleteButton.style.background = 'transparent';
      deleteButton.style.color = 'rgba(255, 255, 255, 0.88)';
    }
  });

  // イベントリスナー
  translateButton.addEventListener('click', handleTranslateClick);
  deleteButton.addEventListener('click', handleDeleteClick);

  container.appendChild(translateButton);
  container.appendChild(deleteButton);
  targetElement.prepend(container);
}

function updateButtonState(state) {
  const translateButton = document.getElementById('ai-translate-button');
  const deleteButton = document.getElementById('ai-delete-button');

  if (!translateButton) return;

  switch (state) {
    case 'loading':
      translateButton.innerHTML = `
        <span style="font-size: 16px; margin-right: 4px; display: inline-block; animation: spin 1s linear infinite;">⏳</span>
        <span>翻訳中...</span>
      `;
      translateButton.disabled = true;
      translateButton.style.opacity = '0.6';
      deleteButton.style.display = 'none';
      break;

    case 'translated':
      translateButton.innerHTML = `
        <span style="font-size: 16px; margin-right: 4px;">📺</span>
        <span>字幕ON</span>
      `;
      translateButton.disabled = false;
      translateButton.style.opacity = '1';
      deleteButton.style.display = 'inline-flex';
      break;

    case 'subtitle_off':
      translateButton.innerHTML = `
        <span style="font-size: 16px; margin-right: 4px;">📺</span>
        <span>字幕ON</span>
      `;
      translateButton.disabled = false;
      translateButton.style.opacity = '1';
      deleteButton.style.display = 'inline-flex';
      break;

    case 'subtitle_on':
      translateButton.innerHTML = `
        <span style="font-size: 16px; margin-right: 4px;">🚫</span>
        <span>字幕OFF</span>
      `;
      translateButton.disabled = false;
      translateButton.style.opacity = '1';
      deleteButton.style.display = 'inline-flex';
      break;

    case 'error':
      translateButton.innerHTML = `
        <span style="font-size: 16px; margin-right: 4px;">⚠️</span>
        <span>エラー</span>
      `;
      translateButton.disabled = false;
      translateButton.style.opacity = '1';
      deleteButton.style.display = 'none';
      break;

    default:
      translateButton.innerHTML = `
        <span style="font-size: 16px; margin-right: 4px;">🌐</span>
        <span>AI翻訳</span>
      `;
      translateButton.disabled = false;
      translateButton.style.opacity = '1';
      deleteButton.style.display = 'none';
      break;
  }
}

// === イベントハンドラー ===
function handleTranslateClick() {
  if (subtitlesData) {
    // 字幕のON/OFF切り替え
    isSubtitleEnabled = !isSubtitleEnabled;
    updateButtonState(isSubtitleEnabled ? 'subtitle_on' : 'subtitle_off');

    if (isSubtitleEnabled) {
      startSubtitleDisplay();
    } else {
      stopSubtitleDisplay();
    }
    return;
  }

  // 新規翻訳
  updateButtonState('loading');

  chrome.runtime.sendMessage({
    type: 'translate',
    videoId: currentVideoId
  }, (response) => {
    if (!chrome.runtime?.id) return;

    if (response && response.success) {
      subtitlesData = response.data.subtitles;
      isSubtitleEnabled = true;
      updateButtonState('translated');
      startSubtitleDisplay();
    } else {
      updateButtonState('error');
      console.error('Translation failed:', response?.error);
    }
  });
}

function handleDeleteClick() {
  if (!confirm('翻訳データを削除しますか？')) return;

  chrome.runtime.sendMessage({
    type: 'delete_translation',
    videoId: currentVideoId
  }, (response) => {
    if (response && response.success) {
      // 状態をリセット
      subtitlesData = null;
      isSubtitleEnabled = false;
      stopSubtitleDisplay();
      updateButtonState('default');
      alert('削除しました');
    }
  });
}

// === 字幕表示（超シンプル） ===
function startSubtitleDisplay() {
  if (!subtitlesData || !isSubtitleEnabled) return;

  // 字幕要素を作成
  if (!subtitleElement) {
    createSubtitleElement();
  }

  // 動画要素を取得
  const video = document.querySelector('video');
  if (!video) return;

  // 既存のリスナーを削除
  video.removeEventListener('timeupdate', updateSubtitle);

  // timeupdate イベントで字幕を更新（デバウンス付き）
  let updateTimeout;
  video.addEventListener('timeupdate', () => {
    if (updateTimeout) clearTimeout(updateTimeout);
    updateTimeout = setTimeout(updateSubtitle, 100); // 100ms デバウンス
  });

  // 初回表示
  updateSubtitle();
}

function stopSubtitleDisplay() {
  const video = document.querySelector('video');
  if (video) {
    video.removeEventListener('timeupdate', updateSubtitle);
  }

  if (subtitleElement) {
    subtitleElement.style.display = 'none';
  }
}

function createSubtitleElement() {
  subtitleElement = document.createElement('div');
  subtitleElement.style.cssText = `
    position: absolute;
    bottom: 60px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 2147483647;
    color: white;
    font-family: 'YouTube Noto', 'Roboto', 'Arial', sans-serif;
    font-weight: 500;
    line-height: 1.4;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    pointer-events: none;
    display: none;
    white-space: nowrap;
    word-break: keep-all;
    overflow: visible;
  `;
  // width は adjustSubtitleWidth で設定するため、初期値は設定しない

  const playerContainer = document.querySelector('#movie_player') ||
    document.querySelector('video').parentElement;
  playerContainer.appendChild(subtitleElement);

  applyStyles();
}

function updateSubtitle() {
  if (!subtitleElement || !isSubtitleEnabled || !subtitlesData) return;

  const video = document.querySelector('video');
  if (!video) return;

  const currentTime = video.currentTime;
  const currentSubtitle = subtitlesData.find(sub =>
    currentTime >= sub.start && currentTime <= sub.end
  );

  if (currentSubtitle && currentSubtitle.text) {
    // 改行コードの包括的処理
    const processedText = currentSubtitle.text.replace(/\\n|\\r\\n|\n|\r/g, '<br>');
    subtitleElement.innerHTML = processedText;

    // 動的幅調整（常に有効）
    console.log('📝 Before adjustSubtitleWidth:', {
      text: currentSubtitle.text,
      currentWidth: subtitleElement.style.width,
      offsetWidth: subtitleElement.offsetWidth
    });

    adjustSubtitleWidth(currentSubtitle.text);

    console.log('✅ After adjustSubtitleWidth:', {
      newWidth: subtitleElement.style.width,
      offsetWidth: subtitleElement.offsetWidth,
      display: subtitleElement.style.display
    });

    subtitleElement.style.display = 'block';
  } else {
    subtitleElement.style.display = 'none';
  }
}

// === 動的幅調整関数（remベース） ===
function adjustSubtitleWidth(text) {
  if (!subtitleElement || !AUTO_SETTINGS.autoWidthEnabled) return;

  // 改行を含む場合の行数計算（未使用のため削除）

  // 各行の文字幅を計算（全角・半角を考慮）
  const lineTexts = text.split(/\\n|\\r\\n|\n|\r/);
  let maxLineWidth = 0;

  lineTexts.forEach(line => {
    let lineWidth = 0;
    for (let char of line) {
      // 半角文字（ASCII）は0.5、全角文字は1.0として計算
      if (char.match(/[\x00-\x7F]/)) {
        lineWidth += 0.5;
      } else {
        lineWidth += 1.0;
      }
    }
    maxLineWidth = Math.max(maxLineWidth, lineWidth);
  });

  // フォントサイズに基づいた文字幅の計算
  const charWidthRem = userSettings.fontSizeRem;           // 基準幅
  const paddingRem = 1.0;                                  // 左右の余裕

  // 文字幅ベースの計算
  const contentWidthRem = maxLineWidth * charWidthRem;
  const finalWidthRem = contentWidthRem + paddingRem;

  // デバッグログ
  console.log('🎯 Subtitle width calculation:', {
    text: text.substring(0, 50) + '...',
    maxLineWidth: maxLineWidth,
    charWidthRem: charWidthRem,
    finalWidthRem: finalWidthRem,
    fontSize: userSettings.fontSizeRem
  });

  // 幅を適用（remで設定）
  subtitleElement.style.setProperty('width', `${finalWidthRem}rem`, 'important');
  subtitleElement.style.setProperty('min-width', `${finalWidthRem}rem`, 'important');
  subtitleElement.style.setProperty('max-width', `${finalWidthRem}rem`, 'important');

  // 中央揃えの確認
  subtitleElement.style.setProperty('left', '50%', 'important');
  subtitleElement.style.setProperty('transform', 'translateX(-50%)', 'important');

  // 適用後の確認ログ
  console.log('📏 Applied styles:', {
    computedWidth: window.getComputedStyle(subtitleElement).width,
    styleWidth: subtitleElement.style.width,
    offsetWidth: subtitleElement.offsetWidth
  });
}

// === 既存翻訳チェック ===
function checkExistingTranslation() {
  chrome.runtime.sendMessage({
    type: 'get_status',
    videoId: currentVideoId
  }, (response) => {
    if (!chrome.runtime?.id) return;

    if (response && response.success) {
      subtitlesData = response.data.subtitles;
      updateButtonState('subtitle_off');
    }
  });
}

// === ユーティリティ ===
function getVideoId() {
  const params = new URLSearchParams(window.location.search);
  return params.get('v');
}

// === SPA対応（URL変化の監視） ===
new MutationObserver(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    if (location.pathname === '/watch') {
      setTimeout(init, 500); // 少し待ってから初期化
    }
  }
}).observe(document.body, { childList: true, subtree: true });

// === 初期実行 ===
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    if (location.pathname === '/watch') init();
  });
} else {
  if (location.pathname === '/watch') init();
}