document.addEventListener('DOMContentLoaded', () => {
    // 要素の取得（シンプル版）
    const fontSizeSlider = document.getElementById('font-size-slider');
    const fontSizeValue = document.getElementById('font-size-value');
    const bgColorPicker = document.getElementById('bg-color-picker');
    const colorPreview = document.getElementById('color-preview');
    const bgOpacitySlider = document.getElementById('bg-opacity-slider');
    const bgOpacityValue = document.getElementById('bg-opacity-value');

    const defaultSettings = {
        fontSizeRem: 1.5,
        bgColor: '#000000',
        bgOpacity: 0.75
    };

    // 1. 保存済みの設定を読み込む
    if (chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(defaultSettings, (settings) => {
            if (fontSizeSlider) {
                fontSizeSlider.value = settings.fontSizeRem * 10;
            }
            if (fontSizeValue) {
                fontSizeValue.textContent = settings.fontSizeRem + 'rem';
            }
            if (bgColorPicker) {
                bgColorPicker.value = settings.bgColor;
            }
            if (bgOpacitySlider) {
                bgOpacitySlider.value = Math.round(settings.bgOpacity * 100);
            }
            if (bgOpacityValue) {
                bgOpacityValue.textContent = Math.round(settings.bgOpacity * 100) + '%';
            }
            updateColorPreview(settings.bgColor);
        });
    }

    // 2. フォントサイズスライダーの処理
    if (fontSizeSlider) {
        fontSizeSlider.addEventListener('input', () => {
            const newSizeRem = parseInt(fontSizeSlider.value) / 10;
            if (fontSizeValue) {
                fontSizeValue.textContent = newSizeRem + 'rem';
            }
            if (chrome.storage && chrome.storage.local) {
                chrome.storage.local.set({ fontSizeRem: newSizeRem });
            }
        });
    }

    // 3. 背景色ピッカーの処理
    if (bgColorPicker) {
        bgColorPicker.addEventListener('input', () => {
            const newColor = bgColorPicker.value;
            updateColorPreview(newColor);
            if (chrome.storage && chrome.storage.local) {
                chrome.storage.local.set({ bgColor: newColor });
            }
        });
    }

    // 4. 背景透明度スライダーの処理
    if (bgOpacitySlider) {
        bgOpacitySlider.addEventListener('input', () => {
            const newOpacity = parseInt(bgOpacitySlider.value) / 100;
            if (bgOpacityValue) {
                bgOpacityValue.textContent = bgOpacitySlider.value + '%';
            }
            if (chrome.storage && chrome.storage.local) {
                chrome.storage.local.set({ bgOpacity: newOpacity });
            }
        });
    }


    function updateColorPreview(color) {
        if (colorPreview) {
            colorPreview.style.backgroundColor = color;
        }
    }

});