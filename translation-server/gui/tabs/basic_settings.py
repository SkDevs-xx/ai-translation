"""
基本設定タブ：API キー設定、自動起動設定、プロンプト編集
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
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
        
        # メインコンテナ
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # API設定フレーム
        self._create_api_key_section(main_container)
        
        # 下部フレーム（プロンプト設定）
        lower_frame = ttk.Frame(main_container)
        lower_frame.pack(fill="both", expand=True)
        self._create_prompt_section(lower_frame)
    
    
    def _create_api_key_section(self, parent):
        """API キー設定セクションを作成"""
        # APIフレーム
        api_frame = ttk.LabelFrame(parent, text="API設定", padding="10")
        api_frame.pack(fill="x", pady=(0, 10))
        
        # 上部コントロールフレーム
        control_frame = ttk.Frame(api_frame)
        control_frame.pack(fill="x", pady=(0, 10))
        
        # 入力フレーム
        input_frame = ttk.Frame(api_frame)
        input_frame.pack(fill="x")
        
        # API キー入力フィールド
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(input_frame, textvariable=self.api_key_var, width=40, show="*")
        self.api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # 保存ボタン
        save_button = ttk.Button(input_frame, text="保存", command=self._save_api_key, width=10)
        save_button.pack(side="left")
        
        # 表示/非表示トグル
        self.show_key_var = tk.BooleanVar()
        show_check = ttk.Checkbutton(
            control_frame, 
            text="APIキーを表示", 
            variable=self.show_key_var,
            command=self._toggle_api_key_visibility
        )
        show_check.pack(side="left")
        
        # ステータスラベル
        self.api_status_label = ttk.Label(control_frame, text="", foreground="green")
        self.api_status_label.pack(side="left", padx=(20, 0))
        
        # 既存のAPIキーをロード
        self._load_existing_api_key()
    
    
    def _create_prompt_section(self, parent):
        """プロンプト設定セクションを作成"""
        # プロンプトフレーム
        prompt_frame = ttk.LabelFrame(parent, text="翻訳プロンプト設定", padding="10")
        prompt_frame.pack(fill="both", expand=True)
        
        
        # テキストエリアフレーム
        text_frame = ttk.Frame(prompt_frame)
        text_frame.pack(fill="both", expand=True)
        
        # テキストエリア
        self.prompt_text = tk.Text(text_frame, width=70, height=15, wrap=tk.WORD)
        self.prompt_text.pack(side="left", fill="both", expand=True)
        
        # テキスト変更時の自動保存設定
        self.prompt_text.bind('<<Modified>>', self._on_prompt_modified)
        self._prompt_save_timer = None
        
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
            command=self._reset_prompt,
            width=20
        )
        reset_button.pack(side="left", padx=(0, 10))
        
        # 保存ボタン
        save_prompt_button = ttk.Button(
            button_frame,
            text="プロンプトを保存",
            command=self._save_prompt,
            width=20
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
    
    def _on_prompt_modified(self, event):
        """プロンプトが変更されたときの処理"""
        if self.prompt_text.edit_modified():
            # 既存のタイマーがあればキャンセル
            if self._prompt_save_timer:
                self.frame.after_cancel(self._prompt_save_timer)
            
            # 2秒後に自動保存
            self._prompt_save_timer = self.frame.after(2000, self._auto_save_prompt)
            
            # 変更フラグをリセット
            self.prompt_text.edit_modified(False)
    
    def _auto_save_prompt(self):
        """プロンプトを自動保存"""
        prompt = self.prompt_text.get(1.0, tk.END).strip()
        if hasattr(self.server_manager, 'set_prompt'):
            self.server_manager.set_prompt(prompt)
            self.prompt_status_label.config(text="✓ 自動保存されました", foreground="green")
            logger.info("プロンプトを自動保存しました")
            
            # 3秒後にステータスをクリア
            self.frame.after(3000, lambda: self.prompt_status_label.config(text=""))
        
        self._prompt_save_timer = None
    
    
    def _load_current_prompt(self):
        """現在のプロンプトを読み込む"""
        if hasattr(self.server_manager, 'get_current_prompt'):
            prompt = self.server_manager.get_current_prompt()
            # 一時的に変更イベントを無効化
            self.prompt_text.bind('<<Modified>>', '')
            self.prompt_text.delete(1.0, tk.END)
            self.prompt_text.insert(1.0, prompt)
            # 変更フラグを明示的にリセット
            self.prompt_text.edit_modified(False)
            # 変更イベントを再有効化
            self.prompt_text.bind('<<Modified>>', self._on_prompt_modified)
    
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
        # 一時的に変更イベントを無効化
        self.prompt_text.bind('<<Modified>>', '')
        self.prompt_text.delete(1.0, tk.END)
        self.prompt_text.insert(1.0, DEFAULT_PROMPT)
        # 変更フラグを明示的にリセット
        self.prompt_text.edit_modified(False)
        # 変更イベントを再有効化
        self.prompt_text.bind('<<Modified>>', self._on_prompt_modified)
        
        if hasattr(self.server_manager, 'set_prompt'):
            self.server_manager.set_prompt(DEFAULT_PROMPT)
            self.prompt_status_label.config(text="✓ デフォルトに戻しました", foreground="green")
            logger.info("プロンプトをデフォルトに戻しました")
            
            # 3秒後にステータスをクリア
            self.frame.after(3000, lambda: self.prompt_status_label.config(text=""))
    
