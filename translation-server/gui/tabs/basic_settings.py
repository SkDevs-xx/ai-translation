"""
基本設定タブ：API キー設定、自動起動設定、プロンプト編集
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from utils.registry import is_auto_start_enabled, set_auto_start
from core.config import DEFAULT_PROMPT

logger = logging.getLogger(__name__)


class BasicSettingsTab:
    """基本設定タブクラス"""
    
    def __init__(self, parent, security_manager, server_manager, on_api_key_saved=None):
        self.security_manager = security_manager
        self.server_manager = server_manager
        self.on_api_key_saved = on_api_key_saved
        
        # フレーム作成
        self.frame = ttk.Frame(parent)
        
        # スクロール可能なキャンバスを作成
        canvas = tk.Canvas(self.frame)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 各セクションを作成
        self._create_api_key_section()
        self._create_auto_start_section()
        self._create_prompt_section()
        
        # レイアウト
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_api_key_section(self):
        """API キー設定セクションを作成"""
        # APIキーフレーム
        api_frame = ttk.LabelFrame(self.scrollable_frame, text="API Key設定", padding="10")
        api_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # 説明
        desc_label = ttk.Label(api_frame, text="Google Gemini APIキーを入力してください（暗号化して保存されます）")
        desc_label.pack(anchor="w", pady=(0, 10))
        
        # 入力フレーム
        input_frame = ttk.Frame(api_frame)
        input_frame.pack(fill="x")
        
        # API キー入力フィールド
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(input_frame, textvariable=self.api_key_var, width=50, show="*")
        self.api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # 保存ボタン
        save_button = ttk.Button(input_frame, text="保存", command=self._save_api_key)
        save_button.pack(side="left")
        
        # 表示/非表示トグル
        self.show_key_var = tk.BooleanVar()
        show_check = ttk.Checkbutton(
            api_frame, 
            text="APIキーを表示", 
            variable=self.show_key_var,
            command=self._toggle_api_key_visibility
        )
        show_check.pack(anchor="w", pady=(5, 0))
        
        # ステータスラベル
        self.api_status_label = ttk.Label(api_frame, text="", foreground="green")
        self.api_status_label.pack(anchor="w", pady=(10, 0))
        
        # 既存のAPIキーをロード
        self._load_existing_api_key()
    
    def _create_auto_start_section(self):
        """自動起動設定セクションを作成"""
        # 自動起動フレーム
        auto_frame = ttk.LabelFrame(self.scrollable_frame, text="起動設定", padding="10")
        auto_frame.pack(fill="x", padx=20, pady=10)
        
        # チェックボックス
        self.auto_start_var = tk.BooleanVar()
        self.auto_start_check = ttk.Checkbutton(
            auto_frame,
            text="Windows起動時に自動的に開始",
            variable=self.auto_start_var,
            command=self._toggle_auto_start
        )
        self.auto_start_check.pack(anchor="w")
        
        # 現在の設定を読み込み
        self.auto_start_var.set(is_auto_start_enabled())
    
    def _create_prompt_section(self):
        """プロンプト設定セクションを作成"""
        # プロンプトフレーム
        prompt_frame = ttk.LabelFrame(self.scrollable_frame, text="翻訳プロンプト設定", padding="10")
        prompt_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        # 説明ラベル
        desc_label = ttk.Label(prompt_frame, text="翻訳時に使用するプロンプトをカスタマイズできます:")
        desc_label.pack(anchor="w", pady=(0, 10))
        
        # テキストエリアフレーム
        text_frame = ttk.Frame(prompt_frame)
        text_frame.pack(fill="both", expand=True)
        
        # テキストエリア
        self.prompt_text = tk.Text(text_frame, width=70, height=15, wrap=tk.WORD)
        self.prompt_text.pack(side="left", fill="both", expand=True)
        
        # スクロールバー
        text_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.prompt_text.yview)
        text_scrollbar.pack(side="right", fill="y")
        self.prompt_text.configure(yscrollcommand=text_scrollbar.set)
        
        # ボタンフレーム
        button_frame = ttk.Frame(prompt_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        # デフォルトに戻すボタン
        reset_button = ttk.Button(
            button_frame,
            text="デフォルトに戻す",
            command=self._reset_prompt
        )
        reset_button.pack(side="left", padx=(0, 10))
        
        # 保存ボタン
        save_prompt_button = ttk.Button(
            button_frame,
            text="プロンプトを保存",
            command=self._save_prompt
        )
        save_prompt_button.pack(side="left")
        
        # プロンプトステータス
        self.prompt_status_label = ttk.Label(button_frame, text="", foreground="green")
        self.prompt_status_label.pack(side="left", padx=(20, 0))
        
        # 現在のプロンプトを読み込む
        self._load_current_prompt()
    
    def _load_existing_api_key(self):
        """既存のAPIキーを読み込み"""
        api_key = self.security_manager.load_api_key()
        if api_key:
            self.api_key_var.set(api_key)
            self.api_status_label.config(text="✓ APIキーが設定されています", foreground="green")
        else:
            self.api_status_label.config(text="⚠ APIキーが設定されていません", foreground="orange")
    
    def _save_api_key(self):
        """APIキーを保存"""
        api_key = self.api_key_var.get().strip()
        
        if not api_key:
            messagebox.showwarning("警告", "APIキーを入力してください")
            return
        
        try:
            self.security_manager.save_api_key(api_key)
            self.api_status_label.config(text="✓ APIキーを保存しました", foreground="green")
            messagebox.showinfo("成功", "APIキーを安全に保存しました")
            
            # コールバックを実行
            if self.on_api_key_saved:
                self.on_api_key_saved()
                
        except Exception as e:
            logger.error(f"APIキー保存エラー: {e}")
            self.api_status_label.config(text="✗ 保存に失敗しました", foreground="red")
            messagebox.showerror("エラー", f"APIキーの保存に失敗しました: {str(e)}")
    
    def _toggle_api_key_visibility(self):
        """APIキーの表示/非表示を切り替え"""
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
    
    def _toggle_auto_start(self):
        """自動起動設定を切り替え"""
        try:
            enabled = self.auto_start_var.get()
            success = set_auto_start(enabled)
            
            if success:
                message = "自動起動を有効にしました" if enabled else "自動起動を無効にしました"
                logger.info(message)
            else:
                self.auto_start_var.set(not enabled)  # 元に戻す
                messagebox.showerror("エラー", "自動起動設定の変更に失敗しました")
                
        except Exception as e:
            logger.error(f"自動起動設定エラー: {e}")
            self.auto_start_var.set(not self.auto_start_var.get())  # 元に戻す
            messagebox.showerror("エラー", f"設定変更エラー: {str(e)}")
    
    def _load_current_prompt(self):
        """現在のプロンプトを読み込む"""
        if hasattr(self.server_manager, 'get_current_prompt'):
            prompt = self.server_manager.get_current_prompt()
            self.prompt_text.delete(1.0, tk.END)
            self.prompt_text.insert(1.0, prompt)
    
    def _save_prompt(self):
        """プロンプトを保存"""
        prompt = self.prompt_text.get(1.0, tk.END).strip()
        if hasattr(self.server_manager, 'set_prompt'):
            self.server_manager.set_prompt(prompt)
            self.prompt_status_label.config(text="✓ 保存しました", foreground="green")
            logger.info("プロンプトを保存しました")
            
            # 3秒後にステータスをクリア
            self.frame.after(3000, lambda: self.prompt_status_label.config(text=""))
    
    def _reset_prompt(self):
        """プロンプトをデフォルトに戻す"""
        self.prompt_text.delete(1.0, tk.END)
        self.prompt_text.insert(1.0, DEFAULT_PROMPT)
        if hasattr(self.server_manager, 'set_prompt'):
            self.server_manager.set_prompt(DEFAULT_PROMPT)
            self.prompt_status_label.config(text="✓ デフォルトに戻しました", foreground="green")
            logger.info("プロンプトをデフォルトに戻しました")
            
            # 3秒後にステータスをクリア
            self.frame.after(3000, lambda: self.prompt_status_label.config(text=""))