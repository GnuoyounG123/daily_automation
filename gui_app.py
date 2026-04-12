#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Automation - 桌面配置中心
原生 Tkinter GUI，无需额外依赖
双击即用，零配置启动
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import threading
import base64
import subprocess
import sys
import webbrowser
from pathlib import Path
from datetime import datetime

from config_manager import ConfigManager


def _get_app_dir() -> Path:
    """获取应用程序目录（兼容打包环境）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


class DailyAutomationApp:
    """主应用程序"""

    @staticmethod
    def _decode_pwd(value: str) -> str:
        if value and value.startswith("enc:"):
            try:
                return base64.b64decode(value[4:]).decode('utf-8')
            except Exception:
                return value
        return value

    @staticmethod
    def _encode_pwd(value: str) -> str:
        if value and not value.startswith("enc:"):
            return "enc:" + base64.b64encode(value.encode('utf-8')).decode('utf-8')
        return value

    def __init__(self, root):
        self.root = root
        self.root.title("📚 Daily Automation - 学术自动化助手")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # 初始化配置管理器（使用正确的应用目录）
        self.app_dir = _get_app_dir()
        self.config_manager = ConfigManager(self.app_dir)

        # 创建界面
        self.create_ui()

        # 加载配置
        self.load_all_config()

    def create_ui(self):
        """创建主界面"""
        # 创建 Notebook（标签页）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # 创建各个标签页
        self.create_home_tab()
        self.create_sources_tab()
        self.create_keywords_tab()
        self.create_reminders_tab()
        self.create_email_tab()
        self.create_api_keys_tab()
        self.create_schedule_tab()
        self.create_about_tab()

        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        status_bar.pack(fill='x', side='bottom')

    # ========== 首页 ==========
    def create_home_tab(self):
        """首页 - 概览和快速操作"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🏠 首页")

        # 标题
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill='x', pady=20)
        ttk.Label(title_frame, text="📚 Daily Automation", font=('Microsoft YaHei', 24, 'bold')).pack()
        ttk.Label(title_frame, text="学术自动化助手 - 让信息找上门", font=('Microsoft YaHei', 12)).pack()

        # 状态卡片
        card_frame = ttk.LabelFrame(frame, text="状态概览")
        card_frame.pack(fill='x', padx=20, pady=10)

        self.status_labels = {}
        stats = [('news_count', '新闻源', '0'), ('keyword_count', '关键词', '0'),
                 ('reminder_count', '提醒', '0'), ('email_status', '邮件', '未配置')]

        for i, (key, label, default) in enumerate(stats):
            col = ttk.Frame(card_frame)
            col.pack(side='left', expand=True, padx=20, pady=10)
            ttk.Label(col, text=label, font=('Microsoft YaHei', 10)).pack()
            self.status_labels[key] = ttk.Label(col, text=default, font=('Microsoft YaHei', 16, 'bold'))
            self.status_labels[key].pack()

        # 快速操作
        action_frame = ttk.LabelFrame(frame, text="快速操作")
        action_frame.pack(fill='x', padx=20, pady=10)

        btn_frame = ttk.Frame(action_frame)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="📚 学术简报生成", command=self.run_crawl, width=18).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="⏰ 每日日程提醒", command=self.run_remind, width=18).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="📂 打开数据目录", command=self.open_data_dir, width=18).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="📤 导出配置", command=self.export_config, width=18).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="📥 导入配置", command=self.import_config, width=18).pack(side='left', padx=10)

        # 最近运行
        log_frame = ttk.LabelFrame(frame, text="最近运行日志")
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state='disabled')
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)

        self.refresh_home_status()

    def refresh_home_status(self):
        """刷新首页状态"""
        config = self.config_manager.get_config()

        sources = config.get('news_sources', [])
        enabled = len([s for s in sources if s.get('enabled', True)])
        self.status_labels['news_count'].config(text=f"{enabled}/{len(sources)}")

        keywords = config.get('keywords', []) + config.get('keywords_cn', [])
        self.status_labels['keyword_count'].config(text=str(len(keywords)))

        reminders = config.get('reminders', [])
        self.status_labels['reminder_count'].config(text=str(len(reminders)))

        email = config.get('email', {})
        self.status_labels['email_status'].config(
            text="已启用" if email.get('enabled') else "未启用"
        )

        # 加载最近日志
        self.load_recent_logs()

    def load_recent_logs(self):
        """加载最近日志"""
        log_dir = self.app_dir / "logs"
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)

        if log_dir.exists():
            log_files = sorted(log_dir.glob("*.log"), key=lambda x: x.name, reverse=True)[:3]
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[-20:]  # 最后20行
                        self.log_text.insert(tk.END, f"=== {log_file.name} ===" + "\n")
                        self.log_text.insert(tk.END, ''.join(lines) + "\n\n")
                except Exception:
                    pass  # 日志文件读取失败可忽略
        else:
            self.log_text.insert(tk.END, "暂无运行记录")

        self.log_text.config(state='disabled')

    # ========== 新闻源管理 ==========
    def create_sources_tab(self):
        """新闻源管理"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📰 新闻源")

        # 列表区域
        list_frame = ttk.LabelFrame(frame, text="已配置的新闻源")
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Treeview
        columns = ('name', 'url', 'type', 'enabled')
        self.sources_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)

        self.sources_tree.heading('name', text='名称')
        self.sources_tree.heading('url', text='URL')
        self.sources_tree.heading('type', text='类型')
        self.sources_tree.heading('enabled', text='状态')

        self.sources_tree.column('name', width=120)
        self.sources_tree.column('url', width=350)
        self.sources_tree.column('type', width=80)
        self.sources_tree.column('enabled', width=80)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.sources_tree.yview)
        self.sources_tree.configure(yscrollcommand=scrollbar.set)

        self.sources_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 操作按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="➕ 添加", command=self.add_source).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="✏️ 编辑", command=self.edit_source).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🗑️ 删除", command=self.delete_source).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🔄 切换状态", command=self.toggle_source).pack(side='left', padx=5)

    def load_sources(self):
        """加载新闻源列表"""
        for item in self.sources_tree.get_children():
            self.sources_tree.delete(item)

        sources = self.config_manager.get_news_sources()
        for source in sources:
            enabled = "✅ 启用" if source.get('enabled', True) else "❌ 禁用"
            self.sources_tree.insert('', 'end', values=(
                source.get('name', ''),
                source.get('url', ''),
                source.get('type', 'rss'),
                enabled
            ))

    def add_source(self):
        """添加新闻源"""
        dialog = SourceDialog(self.root, "添加新闻源")
        if dialog.result:
            self.config_manager.add_news_source(**dialog.result)
            self.load_sources()
            self.refresh_home_status()
            messagebox.showinfo("成功", "新闻源已添加")

    def edit_source(self):
        """编辑新闻源"""
        selected = self.sources_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要编辑的新闻源")
            return

        index = self.sources_tree.index(selected[0])
        sources = self.config_manager.get_news_sources()
        source = sources[index]

        dialog = SourceDialog(self.root, "编辑新闻源", source)
        if dialog.result:
            self.config_manager.update_news_source(index, **dialog.result)
            self.load_sources()
            messagebox.showinfo("成功", "新闻源已更新")

    def delete_source(self):
        """删除新闻源"""
        selected = self.sources_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要删除的新闻源")
            return

        if messagebox.askyesno("确认", "确定要删除此新闻源吗？"):
            index = self.sources_tree.index(selected[0])
            self.config_manager.delete_news_source(index)
            self.load_sources()
            self.refresh_home_status()

    def toggle_source(self):
        """切换新闻源状态"""
        selected = self.sources_tree.selection()
        if not selected:
            return

        index = self.sources_tree.index(selected[0])
        sources = self.config_manager.get_news_sources()
        current = sources[index].get('enabled', True)
        self.config_manager.update_news_source(index, enabled=not current)
        self.load_sources()

    # ========== 关键词管理 ==========
    def create_keywords_tab(self):
        """关键词管理"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🔑 关键词")

        ttk.Label(frame, text="设置用于筛选学术信息的关键词（每行一个）", font=('Microsoft YaHei', 10)).pack(pady=10)

        col_frame = ttk.Frame(frame)
        col_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # 英文关键词
        en_frame = ttk.LabelFrame(col_frame, text="英文关键词")
        en_frame.pack(side='left', fill='both', expand=True, padx=5)

        self.en_keywords_text = scrolledtext.ScrolledText(en_frame, width=40)
        self.en_keywords_text.pack(fill='both', expand=True, padx=5, pady=5)

        # 中文关键词
        cn_frame = ttk.LabelFrame(col_frame, text="中文关键词")
        cn_frame.pack(side='left', fill='both', expand=True, padx=5)

        self.cn_keywords_text = scrolledtext.ScrolledText(cn_frame, width=40)
        self.cn_keywords_text.pack(fill='both', expand=True, padx=5, pady=5)

        # 保存按钮
        ttk.Button(frame, text="💾 保存关键词", command=self.save_keywords).pack(pady=10)

        # 关键词建议
        suggest_frame = ttk.LabelFrame(frame, text="💡 关键词建议")
        suggest_frame.pack(fill='x', padx=10, pady=5)

        suggestions = "学术研究: artificial intelligence, machine learning, deep learning\n" \
                     "公共管理: public governance, digital governance, e-government\n" \
                     "数据科学: big data, data mining, algorithm"
        ttk.Label(suggest_frame, text=suggestions, justify='left').pack(padx=10, pady=5)

    def load_keywords(self):
        """加载关键词"""
        keywords = self.config_manager.get_keywords()

        self.en_keywords_text.delete(1.0, tk.END)
        self.en_keywords_text.insert(tk.END, '\n'.join(keywords.get('keywords', [])))

        self.cn_keywords_text.delete(1.0, tk.END)
        self.cn_keywords_text.insert(tk.END, '\n'.join(keywords.get('keywords_cn', [])))

    def save_keywords(self):
        """保存关键词"""
        en_text = self.en_keywords_text.get(1.0, tk.END)
        cn_text = self.cn_keywords_text.get(1.0, tk.END)

        en_keywords = [k.strip() for k in en_text.split('\n') if k.strip()]
        cn_keywords = [k.strip() for k in cn_text.split('\n') if k.strip()]

        if self.config_manager.update_keywords(en_keywords, cn_keywords):
            messagebox.showinfo("成功", "关键词已保存")
            self.refresh_home_status()

    # ========== 提醒管理 ==========
    def create_reminders_tab(self):
        """提醒管理"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⏰ 提醒")

        # 列表
        list_frame = ttk.LabelFrame(frame, text="已配置的提醒")
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        columns = ('time', 'title', 'description')
        self.reminders_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)

        self.reminders_tree.heading('time', text='时间')
        self.reminders_tree.heading('title', text='标题')
        self.reminders_tree.heading('description', text='描述')

        self.reminders_tree.column('time', width=80)
        self.reminders_tree.column('title', width=150)
        self.reminders_tree.column('description', width=400)

        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.reminders_tree.yview)
        self.reminders_tree.configure(yscrollcommand=scrollbar.set)

        self.reminders_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="➕ 添加", command=self.add_reminder).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="✏️ 编辑", command=self.edit_reminder).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🗑️ 删除", command=self.delete_reminder).pack(side='left', padx=5)

    def load_reminders(self):
        """加载提醒列表"""
        for item in self.reminders_tree.get_children():
            self.reminders_tree.delete(item)

        reminders = self.config_manager.get_reminders()
        for r in reminders:
            self.reminders_tree.insert('', 'end', values=(
                r.get('time', ''),
                r.get('title', ''),
                r.get('description', '')
            ))

    def add_reminder(self):
        """添加提醒"""
        dialog = ReminderDialog(self.root, "添加提醒")
        if dialog.result:
            self.config_manager.add_reminder(**dialog.result)
            self.load_reminders()
            self.refresh_home_status()
            messagebox.showinfo("成功", "提醒已添加")

    def edit_reminder(self):
        """编辑提醒"""
        selected = self.reminders_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要编辑的提醒")
            return

        index = self.reminders_tree.index(selected[0])
        reminders = self.config_manager.get_reminders()
        reminder = reminders[index]

        dialog = ReminderDialog(self.root, "编辑提醒", reminder)
        if dialog.result:
            self.config_manager.update_reminder(index, **dialog.result)
            self.load_reminders()
            messagebox.showinfo("成功", "提醒已更新")

    def delete_reminder(self):
        """删除提醒"""
        selected = self.reminders_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要删除的提醒")
            return

        if messagebox.askyesno("确认", "确定要删除此提醒吗？"):
            index = self.reminders_tree.index(selected[0])
            self.config_manager.delete_reminder(index)
            self.load_reminders()
            self.refresh_home_status()

    # ========== 邮箱配置 ==========
    def create_email_tab(self):
        """邮箱配置"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📧 邮箱")

        # 启用开关
        self.email_enabled = tk.BooleanVar()
        ttk.Checkbutton(frame, text="启用邮件发送", variable=self.email_enabled).pack(pady=10)

        # 配置表单
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill='x', padx=20, pady=10)

        labels = ['SMTP服务器:', 'SMTP端口:', '发件人邮箱:', '授权密码:', '收件人邮箱:', '邮件主题前缀:']
        self.email_entries = {}

        for i, label in enumerate(labels):
            row = ttk.Frame(form_frame)
            row.pack(fill='x', pady=5)

            ttk.Label(row, text=label, width=15).pack(side='left')

            key = label.replace(':', '').replace(' ', '_')
            entry = ttk.Entry(row, width=50)
            if '密码' in label:
                entry.config(show='*')
            entry.pack(side='left', padx=5)
            self.email_entries[key] = entry

        ttk.Button(frame, text="💾 保存邮箱配置", command=self.save_email_config).pack(pady=15)

        # 常用配置说明
        help_frame = ttk.LabelFrame(frame, text="📋 常用邮箱SMTP配置")
        help_frame.pack(fill='x', padx=20, pady=10)

        help_text = """
QQ邮箱: smtp.qq.com 端口587 (需要开启SMTP服务并获取授权码)
163邮箱: smtp.163.com 端口25 (需要开启SMTP服务)
Gmail: smtp.gmail.com 端口587 (需要应用专用密码)
Outlook: smtp-mail.outlook.com 端口587
        """
        ttk.Label(help_frame, text=help_text, justify='left').pack(padx=10, pady=5)

    def load_email_config(self):
        """加载邮箱配置"""
        email = self.config_manager.get_email_config()
        self.email_enabled.set(email.get('enabled', False))
        self.email_entries['SMTP服务器'].insert(0, email.get('smtp_server', 'smtp.qq.com'))
        self.email_entries['SMTP端口'].insert(0, str(email.get('smtp_port', 587)))
        self.email_entries['发件人邮箱'].insert(0, email.get('sender_email', ''))
        self.email_entries['授权密码'].insert(0, self._decode_pwd(email.get('sender_password', '')))
        self.email_entries['收件人邮箱'].insert(0, email.get('receiver_email', ''))
        self.email_entries['邮件主题前缀'].insert(0, email.get('subject_prefix', '[学术简报]'))

    def save_email_config(self):
        """保存邮箱配置"""
        config = {
            'enabled': self.email_enabled.get(),
            'smtp_server': self.email_entries['SMTP服务器'].get(),
            'smtp_port': int(self.email_entries['SMTP端口'].get() or 587),
            'sender_email': self.email_entries['发件人邮箱'].get(),
            'sender_password': self._encode_pwd(self.email_entries['授权密码'].get()),
            'receiver_email': self.email_entries['收件人邮箱'].get(),
            'subject_prefix': self.email_entries['邮件主题前缀'].get()
        }

        if self.config_manager.update_email_config(config):
            messagebox.showinfo("成功", "邮箱配置已保存")
            self.refresh_home_status()

    # ========== API密钥配置 ==========
    def create_api_keys_tab(self):
        """API密钥配置"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🔑 API密钥")

        ttk.Label(frame, text="学术API密钥配置",
                  font=('Microsoft YaHei', 14, 'bold')).pack(pady=10)
        ttk.Label(frame, text="配置API密钥可提升访问速率和配额，部分API必须配置密钥才能使用",
                  foreground='gray').pack(pady=5)

        # 配置表单
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill='x', padx=20, pady=10)

        self.api_key_entries = {}
        api_key_config = [
            ('semantic_scholar', 'Semantic Scholar:', '可选 - 无Key限流100次/5分钟'),
            ('openalex', 'OpenAlex:', '可选 - 有Key可提升速率'),
            ('core', 'CORE:', '必须 - 无Key无法使用'),
        ]

        for i, (key_name, label, hint) in enumerate(api_key_config):
            row = ttk.Frame(form_frame)
            row.pack(fill='x', pady=8)

            ttk.Label(row, text=label, width=18).pack(side='left')

            entry = ttk.Entry(row, width=50, show='*')
            entry.pack(side='left', padx=5)
            self.api_key_entries[key_name] = entry

            ttk.Label(row, text=hint, foreground='gray').pack(side='left', padx=5)

        # 显示/隐藏密钥切换
        self.show_api_keys = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="显示密钥", variable=self.show_api_keys,
                        command=self._toggle_api_key_visibility).pack(pady=5)

        ttk.Button(frame, text="💾 保存API密钥配置",
                   command=self.save_api_keys_config).pack(pady=10)

        # 获取API Key链接
        help_frame = ttk.LabelFrame(frame, text="🔗 获取API密钥")
        help_frame.pack(fill='x', padx=20, pady=10)

        links = [
            ("Semantic Scholar API Key", "https://www.semanticscholar.org/product/api#api-key"),
            ("OpenAlex API Key", "https://docs.openalex.org/how-to-use-the-api/get-an-api-key"),
            ("CORE API Key", "https://core.ac.uk/services/api"),
        ]

        for name, url in links:
            link_frame = ttk.Frame(help_frame)
            link_frame.pack(fill='x', padx=10, pady=3)
            ttk.Label(link_frame, text=f"• {name}:").pack(side='left')
            link_label = ttk.Label(link_frame, text=url, foreground='blue', cursor='hand2')
            link_label.pack(side='left', padx=5)
            link_label.bind('<Button-1>', lambda e, u=url: webbrowser.open(u))

        # 缺失密钥提醒
        self.api_key_status = ttk.Label(frame, text="", foreground='orange')
        self.api_key_status.pack(pady=5)

    def _toggle_api_key_visibility(self):
        show = self.show_api_keys.get()
        for entry in self.api_key_entries.values():
            entry.config(show='' if show else '*')

    def load_api_keys_config(self):
        """加载API密钥配置"""
        if not hasattr(self, 'api_key_entries'):
            return
        keys = self.config_manager.get_api_keys()
        for key_name, entry in self.api_key_entries.items():
            entry.delete(0, tk.END)
            value = keys.get(key_name, '')
            if value and value.startswith('enc:'):
                value = self._decode_pwd(value)
            entry.insert(0, value)

        self._check_api_key_status()

    def save_api_keys_config(self):
        """保存API密钥配置"""
        api_keys = {}
        for key_name, entry in self.api_key_entries.items():
            value = entry.get().strip()
            if value and not value.startswith('enc:'):
                value = self._encode_pwd(value)
            api_keys[key_name] = value

        if self.config_manager.update_api_keys(api_keys):
            messagebox.showinfo("成功", "API密钥配置已保存")
            self._check_api_key_status()
            self.refresh_home_status()

    def _check_api_key_status(self):
        """检查API密钥状态并提醒"""
        if not hasattr(self, 'api_key_entries'):
            return
        missing = self.config_manager.check_missing_api_keys()
        if missing:
            required_missing = [m for m in missing if m['required']]
            optional_missing = [m for m in missing if not m['required']]
            msg_parts = []
            if required_missing:
                names = ', '.join(m['name'] for m in required_missing)
                msg_parts.append(f"⚠️ 必须配置: {names}")
            if optional_missing:
                names = ', '.join(m['name'] for m in optional_missing)
                msg_parts.append(f"💡 建议配置: {names}")
            self.api_key_status.config(text=' | '.join(msg_parts))
        else:
            self.api_key_status.config(text="✅ 所有API密钥已配置", foreground='green')

    # ========== 课程表 ==========
    def create_schedule_tab(self):
        """课程表管理"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📅 课程表")

        # 日期选择
        select_frame = ttk.Frame(frame)
        select_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(select_frame, text="选择日期:").pack(side='left')
        self.day_var = tk.StringVar()
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        self.day_combo = ttk.Combobox(select_frame, textvariable=self.day_var, values=day_names, width=10, state='readonly')
        self.day_combo.current(0)
        self.day_combo.pack(side='left', padx=10)
        self.day_combo.bind('<<ComboboxSelected>>', self.on_day_change)

        self.day_map = dict(zip(day_names, days))

        # 课程列表
        list_frame = ttk.LabelFrame(frame, text="当日课程")
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        columns = ('name', 'time', 'location', 'teacher')
        self.schedule_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)

        self.schedule_tree.heading('name', text='课程名称')
        self.schedule_tree.heading('time', text='时间')
        self.schedule_tree.heading('location', text='地点')
        self.schedule_tree.heading('teacher', text='教师')

        self.schedule_tree.column('name', width=200)
        self.schedule_tree.column('time', width=120)
        self.schedule_tree.column('location', width=200)
        self.schedule_tree.column('teacher', width=100)

        self.schedule_tree.pack(fill='both', expand=True)

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(btn_frame, text="➕ 添加课程", command=self.add_course).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🗑️ 删除课程", command=self.delete_course).pack(side='left', padx=5)

    def load_schedule(self):
        """加载课程表"""
        self.on_day_change(None)

    def on_day_change(self, event):
        """日期变更"""
        for item in self.schedule_tree.get_children():
            self.schedule_tree.delete(item)

        day_name = self.day_var.get()
        day = self.day_map.get(day_name, 'Monday')

        schedule = self.config_manager.get_week_schedule()
        courses = schedule.get(day, [])

        for course in courses:
            self.schedule_tree.insert('', 'end', values=(
                course.get('name', ''),
                course.get('time', ''),
                course.get('location', ''),
                course.get('teacher', '')
            ))

    def add_course(self):
        """添加课程"""
        day_name = self.day_var.get()
        day = self.day_map.get(day_name, 'Monday')

        dialog = CourseDialog(self.root, "添加课程")
        if dialog.result:
            self.config_manager.add_course(day, **dialog.result)
            self.on_day_change(None)
            messagebox.showinfo("成功", "课程已添加")

    def delete_course(self):
        """删除课程"""
        selected = self.schedule_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择要删除的课程")
            return

        if messagebox.askyesno("确认", "确定要删除此课程吗？"):
            day_name = self.day_var.get()
            day = self.day_map.get(day_name, 'Monday')
            index = self.schedule_tree.index(selected[0])
            self.config_manager.delete_course(day, index)
            self.on_day_change(None)

    # ========== 关于 ==========
    def create_about_tab(self):
        """关于页面"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="ℹ️ 关于")

        ttk.Label(frame, text="📚 Daily Automation", font=('Microsoft YaHei', 20, 'bold')).pack(pady=30)
        ttk.Label(frame, text="学术自动化助手 v1.0", font=('Microsoft YaHei', 12)).pack()
        ttk.Label(frame, text="让信息找上门，省下时间做重要的事", font=('Microsoft YaHei', 10)).pack(pady=10)

        ttk.Separator(frame, orient='horizontal').pack(fill='x', padx=50, pady=20)

        # 功能说明
        features = ttk.LabelFrame(frame, text="功能特性")
        features.pack(fill='x', padx=50, pady=10)

        feature_text = """
✅ 多源学术信息爬取（arXiv、Semantic Scholar等）
✅ 智能关键词筛选
✅ 每日简报生成
✅ 邮件自动发送
✅ 日程提醒
✅ 课程表管理
        """
        ttk.Label(features, text=feature_text, justify='left').pack(padx=10, pady=5)

        # 重置按钮
        ttk.Button(frame, text="🔄 重置为默认配置", command=self.reset_config).pack(pady=20)

    def reset_config(self):
        """重置配置"""
        if messagebox.askyesno("确认", "确定要重置为默认配置吗？所有自定义设置将丢失。"):
            self.config_manager.reset_to_default()
            self.load_all_config()
            messagebox.showinfo("成功", "已重置为默认配置")

    # ========== 通用方法 ==========
    def load_all_config(self):
        """加载所有配置"""
        self.load_sources()
        self.load_keywords()
        self.load_reminders()
        self.load_email_config()
        self.load_api_keys_config()
        self.load_schedule()
        self.refresh_home_status()

    def _run_subprocess_task(self, task_mode: str, status_msg: str, success_msg: str):
        """通用子进程任务执行器

        Args:
            task_mode: 任务模式 (all/crawl/remind)
            status_msg: 运行中状态提示
            success_msg: 成功状态提示
        """
        self.status_var.set(status_msg)
        self.root.update()

        def run_task():
            try:
                log_dir = self.app_dir / "logs"
                log_dir.mkdir(exist_ok=True)

                debug_log = log_dir / "gui_debug.log"
                def log(msg):
                    with open(debug_log, 'a', encoding='utf-8') as f:
                        f.write(f"[{datetime.now().isoformat()}] {msg}" + "\n")

                log("=== 任务开始 ===")
                log(f"app_dir: {self.app_dir}")

                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                    log(f"打包模式，运行: {exe_path} --task {task_mode}")

                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE

                    cmd = [exe_path, "--task", task_mode] if task_mode != "all" else [exe_path, "--task"]
                    result = subprocess.run(
                        cmd,
                        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(self.app_dir),
                        timeout=600,
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    script_path = self.app_dir / "daily_assistant.py"
                    log(f"开发模式，运行: {script_path} {task_mode}")
                    result = subprocess.run(
                        [sys.executable, str(script_path), task_mode],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        cwd=str(self.app_dir),
                        timeout=600
                    )

                log(f"返回码: {result.returncode}")
                if result.stdout:
                    log(f"输出: {result.stdout[:500]}")
                if result.stderr:
                    log(f"错误: {result.stderr[:500]}")

                if result.returncode == 0:
                    log("任务执行成功")
                    self.root.after(0, lambda: self.status_var.set(success_msg))
                    self.root.after(0, self.refresh_home_status)
                else:
                    log(f"任务执行失败: {result.returncode}")
                    self.root.after(0, lambda: messagebox.showerror("运行错误", "任务执行失败" + "\n" + f"{result.stderr}"))
                    self.root.after(0, lambda: self.status_var.set("运行失败"))

                log("=== 任务结束 ===")

            except subprocess.TimeoutExpired:
                log("任务超时")
                self.root.after(0, lambda: messagebox.showerror("错误", "任务执行超时"))
                self.root.after(0, lambda: self.status_var.set("运行失败"))
            except Exception as e:
                import traceback
                log(f"异常: {traceback.format_exc()}")
                self.root.after(0, lambda: messagebox.showerror("错误", "执行失败:" + "\n" + f"{str(e)}"))
                self.root.after(0, lambda: self.status_var.set("运行失败"))

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

    def run_once(self):
        """运行一次任务"""
        self._run_subprocess_task("all", "正在运行...", "运行完成")

    def run_crawl(self):
        """运行学术简报生成"""
        self._run_subprocess_task("crawl", "正在生成学术简报...", "学术简报生成完成")

    def run_remind(self):
        """运行每日日程提醒"""
        self._run_subprocess_task("remind", "正在检查日程提醒...", "日程提醒检查完成")


    def open_data_dir(self):
        """打开数据目录"""
        data_dir = self.app_dir / "data"
        data_dir.mkdir(exist_ok=True)
        webbrowser.open(str(data_dir))

    def export_config(self):
        """导出配置"""
        data = self.config_manager.export_all_config()
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"daily_automation_config_{datetime.now().strftime('%Y%m%d')}.json"
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", f"配置已导出到: {filename}")

    def import_config(self):
        """导入配置"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if self.config_manager.import_all_config(data):
                    self.load_all_config()
                    messagebox.showinfo("成功", "配置已导入")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")


# ========== 对话框类 ==========

class SourceDialog:
    """新闻源编辑对话框"""

    def __init__(self, parent, title, source=None):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 表单
        frame = ttk.Frame(self.dialog)
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(frame, text="名称:").grid(row=0, column=0, sticky='e', pady=5)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="URL:").grid(row=1, column=0, sticky='e', pady=5)
        self.url_entry = ttk.Entry(frame, width=40)
        self.url_entry.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="类型:").grid(row=2, column=0, sticky='e', pady=5)
        self.type_var = tk.StringVar(value='rss')
        ttk.Combobox(frame, textvariable=self.type_var, values=['rss', 'web', 'json'], width=37).grid(row=2, column=1, pady=5)

        # 填充初始值
        if source:
            self.name_entry.insert(0, source.get('name', ''))
            self.url_entry.insert(0, source.get('url', ''))
            self.type_var.set(source.get('type', 'rss'))

        # 按钮
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=self.ok).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="取消", command=self.cancel).pack(side='left', padx=10)

        self.dialog.wait_window()

    def ok(self):
        name = self.name_entry.get().strip()
        url = self.url_entry.get().strip()
        if name and url:
            self.result = {
                'name': name,
                'url': url,
                'source_type': self.type_var.get(),
                'enabled': True
            }
            self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()


class ReminderDialog:
    """提醒编辑对话框"""

    def __init__(self, parent, title, reminder=None):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x180")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog)
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        ttk.Label(frame, text="时间 (HH:MM):").grid(row=0, column=0, sticky='e', pady=5)
        self.time_entry = ttk.Entry(frame, width=30)
        self.time_entry.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="标题:").grid(row=1, column=0, sticky='e', pady=5)
        self.title_entry = ttk.Entry(frame, width=30)
        self.title_entry.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="描述:").grid(row=2, column=0, sticky='e', pady=5)
        self.desc_entry = ttk.Entry(frame, width=30)
        self.desc_entry.grid(row=2, column=1, pady=5)

        if reminder:
            self.time_entry.insert(0, reminder.get('time', ''))
            self.title_entry.insert(0, reminder.get('title', ''))
            self.desc_entry.insert(0, reminder.get('description', ''))

        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=self.ok).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="取消", command=self.cancel).pack(side='left', padx=10)

        self.dialog.wait_window()

    def ok(self):
        time_val = self.time_entry.get().strip()
        title = self.title_entry.get().strip()
        desc = self.desc_entry.get().strip()
        if time_val and title:
            self.result = {'time': time_val, 'title': title, 'description': desc}
            self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()


class CourseDialog:
    """课程编辑对话框"""

    def __init__(self, parent, title):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog)
        frame.pack(fill='both', expand=True, padx=20, pady=15)

        fields = [('课程名称:', 'name'), ('时间:', 'time'), ('地点:', 'location'), ('教师:', 'teacher')]
        self.entries = {}

        for i, (label, key) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky='e', pady=3)
            entry = ttk.Entry(frame, width=30)
            entry.grid(row=i, column=1, pady=3)
            self.entries[key] = entry

        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=self.ok).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="取消", command=self.cancel).pack(side='left', padx=10)

        self.dialog.wait_window()

    def ok(self):
        name = self.entries['name'].get().strip()
        time = self.entries['time'].get().strip()
        if name and time:
            self.result = {
                'name': name,
                'time': time,
                'location': self.entries['location'].get().strip(),
                'teacher': self.entries['teacher'].get().strip(),
                'note': ''
            }
            self.dialog.destroy()

    def cancel(self):
        self.dialog.destroy()


# ========== 主程序入口 ==========

def run_task_mode():
    """任务模式：直接运行任务（不启动GUI）"""
    # 设置输出目录为exe所在目录
    if getattr(sys, 'frozen', False):
        app_dir = Path(sys.executable).parent
    else:
        app_dir = Path(__file__).parent

    # 写入日志确认任务模式启动
    log_dir = app_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / "task_mode.log", 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().isoformat()}] 任务模式启动" + "\n")
        f.write(f"app_dir: {app_dir}" + "\n")
        f.write(f"sys.argv: {sys.argv}" + "\n")

    # 导入并运行任务
    sys.path.insert(0, str(app_dir))
    import daily_assistant
    mode = sys.argv[2] if len(sys.argv) > 2 else "all"
    daily_assistant.main(mode=mode)


def main():
    """GUI模式：启动图形界面"""
    root = tk.Tk()
    app = DailyAutomationApp(root)
    root.mainloop()


if __name__ == "__main__":
    # 写入启动日志（无论什么模式）
    app_dir = _get_app_dir()
    log_dir = app_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / "startup.log", 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().isoformat()}] 程序启动" + "\n")
        f.write(f"sys.argv: {sys.argv}" + "\n")
        f.write(f"frozen: {getattr(sys, 'frozen', False)}" + "\n")
        f.write(f"app_dir: {app_dir}" + "\n")

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--task":
        # 任务模式
        run_task_mode()
    else:
        # GUI模式
        main()
