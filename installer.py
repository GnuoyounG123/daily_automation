#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import csv
import re
import shutil
import subprocess
import os
import sys
import ctypes
from pathlib import Path
from datetime import datetime

try:
    from config_manager import DEFAULT_NEWS_SOURCES, SOURCE_CATEGORIES
except ImportError:
    DEFAULT_NEWS_SOURCES = []
    SOURCE_CATEGORIES = {}

POPULAR_SCHOOLS = [
    "\u6d59\u6c5f\u5927\u5b66", "\u6e05\u534e\u5927\u5b66", "\u5317\u4eac\u5927\u5b66", "\u590d\u65e6\u5927\u5b66", "\u4e0a\u6d77\u4ea4\u901a\u5927\u5b66",
    "\u5357\u4eac\u5927\u5b66", "\u4e2d\u56fd\u79d1\u5b66\u6280\u672f\u5927\u5b66", "\u6b66\u6c49\u5927\u5b66", "\u534e\u4e2d\u79d1\u6280\u5927\u5b66", "\u4e2d\u5c71\u5927\u5b66",
    "\u540c\u6d4e\u5927\u5b66", "\u4e1c\u5357\u5927\u5b66", "\u54c8\u5c14\u6ee8\u5de5\u4e1a\u5927\u5b66", "\u897f\u5b89\u4ea4\u901a\u5927\u5b66", "\u5317\u4eac\u822a\u7a7a\u822a\u5929\u5927\u5b66",
    "\u56db\u5ddd\u5927\u5b66", "\u5357\u5f00\u5927\u5b66", "\u5929\u6d25\u5927\u5b66", "\u53a6\u95e8\u5927\u5b66", "\u4e2d\u56fd\u4eba\u6c11\u5927\u5b66",
    "\u5176\u4ed6\uff08\u624b\u52a8\u8f93\u5165\uff09"
]

GRADES = ["\u5927\u4e00", "\u5927\u4e8c", "\u5927\u4e09", "\u5927\u56db", "\u7814\u4e00", "\u7814\u4e8c", "\u7814\u4e09", "\u535a\u4e00", "\u535a\u4e8c", "\u535a\u4e09"]

INTEREST_AREAS = [
    ("\U0001f916 \u4eba\u5de5\u667a\u80fd", ["artificial intelligence", "machine learning", "deep learning", "NLP", "computer vision"], ["\u4eba\u5de5\u667a\u80fd", "\u673a\u5668\u5b66\u4e60", "\u6df1\u5ea6\u5b66\u4e60"]),
    ("\U0001f4ca \u6570\u636e\u79d1\u5b66", ["data science", "big data", "data mining", "statistics", "data analysis"], ["\u6570\u636e\u79d1\u5b66", "\u5927\u6570\u636e", "\u6570\u636e\u6316\u6398"]),
    ("\U0001f4bb \u8ba1\u7b97\u673a\u7cfb\u7edf", ["operating systems", "distributed systems", "cloud computing", "database"], ["\u8ba1\u7b97\u673a\u7cfb\u7edf", "\u5206\u5e03\u5f0f\u7cfb\u7edf", "\u4e91\u8ba1\u7b97"]),
    ("\U0001f512 \u7f51\u7edc\u5b89\u5168", ["cybersecurity", "cryptography", "network security", "privacy"], ["\u7f51\u7edc\u5b89\u5168", "\u5bc6\u7801\u5b66"]),
    ("\U0001f4b0 \u7ecf\u6d4e\u5b66", ["economics", "econometrics", "macroeconomics", "microeconomics"], ["\u7ecf\u6d4e\u5b66", "\u8ba1\u91cf\u7ecf\u6d4e\u5b66"]),
    ("\U0001f4c8 \u91d1\u878d\u5b66", ["finance", "financial engineering", "quantitative finance", "fintech"], ["\u91d1\u878d\u5b66", "\u91d1\u878d\u5de5\u7a0b"]),
    ("\U0001f3db\ufe0f \u516c\u5171\u7ba1\u7406", ["public governance", "public policy", "digital governance", "e-government"], ["\u516c\u5171\u7ba1\u7406", "\u6570\u5b57\u6cbb\u7406"]),
    ("\U0001f9e0 \u5fc3\u7406\u5b66", ["psychology", "cognitive science", "behavioral science"], ["\u5fc3\u7406\u5b66", "\u8ba4\u77e5\u79d1\u5b66"]),
    ("\U0001f3e5 \u533b\u5b66", ["medicine", "biomedical", "clinical research", "public health"], ["\u533b\u5b66", "\u751f\u7269\u533b\u5b66"]),
    ("\U0001f4da \u6559\u80b2\u5b66", ["education", "pedagogy", "educational technology"], ["\u6559\u80b2\u5b66", "\u6559\u80b2\u6280\u672f"]),
    ("\u2696\ufe0f \u6cd5\u5b66", ["law", "jurisprudence", "constitutional law"], ["\u6cd5\u5b66", "\u6cd5\u5f8b"]),
    ("\u270d\ufe0f \u6587\u5b66", ["literature", "linguistics", "cultural studies"], ["\u6587\u5b66", "\u8bed\u8a00\u5b66"]),
    ("\U0001f331 \u73af\u5883\u79d1\u5b66", ["environmental science", "climate change", "sustainability"], ["\u73af\u5883\u79d1\u5b66", "\u6c14\u5019\u53d8\u5316"]),
    ("\U0001f52c \u6750\u6599\u79d1\u5b66", ["materials science", "nanotechnology", "polymer science"], ["\u6750\u6599\u79d1\u5b66", "\u7eb3\u7c73\u6280\u672f"]),
]

DAY_NAMES_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

APP_NAME = "Daily Automation"
APP_EXE_NAME = "DailyAutomation.exe"
DEFAULT_INSTALL_DIR = r"C:\DailyAutomation"

SIDEBAR_BG = "#2c3e50"
SIDEBAR_FG = "#ecf0f1"
SIDEBAR_ACTIVE = "#3498db"
SIDEBAR_DONE = "#27ae60"
CONTENT_BG = "#ffffff"
ACCENT = "#3498db"
ACCENT_HOVER = "#2980b9"
BORDER = "#bdc3c7"


def parse_course_table(text):
    courses = []
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    if not lines:
        return courses
    separator = None
    for line in lines[:5]:
        if '\t' in line:
            separator = '\t'
            break
        elif '|' in line:
            separator = '|'
            break
        elif ',' in line and line.count(',') >= 2:
            separator = ','
            break
    rows = []
    for line in lines:
        if separator:
            parts = [p.strip() for p in line.split(separator)]
        else:
            parts = [p.strip() for p in re.split(r'\s{2,}', line)]
        if len(parts) >= 2:
            non_empty = sum(1 for p in parts if p)
            if non_empty <= 2 and len(parts) > 4:
                continue
            rows.append(parts)
    if not rows:
        return courses
    name_col = time_col = location_col = teacher_col = day_col = -1
    header_idx = -1
    for row_idx, row in enumerate(rows):
        temp_name = temp_time = temp_loc = temp_teacher = temp_day = -1
        found = False
        for i, cell in enumerate(row):
            cl = cell.lower()
            if any(k in cl for k in ['\u8bfe\u7a0b\u540d\u79f0', '\u8bfe\u7a0b\u540d', 'name', 'course name']):
                temp_name = i; found = True
            elif any(k in cl for k in ['\u4e0a\u8bfe\u65f6\u95f4', 'time', '\u8282\u6b21']):
                temp_time = i; found = True
            elif any(k in cl for k in ['\u4e0a\u8bfe\u5730\u70b9', 'location', 'room', '\u5730\u70b9', '\u6559\u5ba4']):
                temp_loc = i; found = True
            elif any(k in cl for k in ['\u6559\u5e08\u59d3\u540d', '\u4efb\u8bfe\u6559\u5e08', 'teacher', '\u6388\u8bfe\u6559\u5e08']):
                temp_teacher = i; found = True
            elif any(k in cl for k in ['\u661f\u671f', 'day', 'week']) and not _looks_like_time_or_day(cell):
                temp_day = i; found = True
        if found and (temp_name >= 0 or temp_time >= 0):
            name_col, time_col, location_col, teacher_col, day_col = temp_name, temp_time, temp_loc, temp_teacher, temp_day
            header_idx = row_idx
            break
    if header_idx < 0:
        first_row = rows[0]
        for i, cell in enumerate(first_row):
            cl = cell.lower()
            if any(k in cl for k in ['\u8bfe\u7a0b\u540d', '\u540d\u79f0', 'course', 'name', '\u79d1\u76ee']):
                name_col = i
            elif any(k in cl for k in ['\u65f6\u95f4', 'time', '\u8282\u6b21']):
                time_col = i
            elif any(k in cl for k in ['\u5730\u70b9', '\u6559\u5ba4', 'location', 'room']):
                location_col = i
            elif any(k in cl for k in ['\u6559\u5e08', 'teacher', '\u6388\u8bfe']):
                teacher_col = i
        if name_col < 0 and time_col < 0:
            if len(first_row) >= 4:
                if _looks_like_time_or_day(first_row[0]):
                    time_col, name_col, teacher_col, location_col = 0, 1, 2, 3
                else:
                    name_col, time_col, location_col, teacher_col = 0, 1, 2, 3
            elif len(first_row) >= 3:
                if _looks_like_time_or_day(first_row[0]):
                    time_col, name_col, location_col = 0, 1, 2
                else:
                    name_col, time_col, location_col = 0, 1, 2
            elif len(first_row) >= 2:
                if _looks_like_time_or_day(first_row[0]):
                    time_col, name_col = 0, 1
                else:
                    name_col, time_col = 0, 1
        header_idx = 0
    data_start = header_idx + 1
    for row in rows[data_start:]:
        if len(row) <= max(name_col, 0):
            continue
        name = row[name_col] if name_col >= 0 and name_col < len(row) else ""
        time_val = row[time_col] if time_col >= 0 and time_col < len(row) else ""
        location = row[location_col] if location_col >= 0 and location_col < len(row) else ""
        teacher = row[teacher_col] if teacher_col >= 0 and teacher_col < len(row) else ""
        day_str = row[day_col] if day_col >= 0 and day_col < len(row) else ""
        if not name:
            continue
        time_parts = [t.strip() for t in time_val.split(';') if t.strip()] if time_val else [""]
        loc_parts = [l.strip() for l in location.split(';') if l.strip()] if location else [""]
        for ti, tp in enumerate(time_parts):
            day = _parse_day(day_str) if day_str else ""
            if not day and tp:
                day = _parse_day(tp)
            if not day:
                day = "Monday"
            clean_time = _strip_day_from_time(tp) if tp and day else tp
            loc = loc_parts[ti] if ti < len(loc_parts) else (loc_parts[-1] if loc_parts else "")
            courses.append({'day': day, 'name': name, 'time': clean_time, 'location': loc, 'teacher': teacher, 'note': ''})
    return courses


def _looks_like_time_or_day(text):
    if not text:
        return False
    if re.search(r'\u5468[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u65e5\u672b1-7]', text):
        return True
    if re.search(r'\u661f\u671f[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u65e5]', text):
        return True
    if re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', text, re.IGNORECASE):
        return True
    if re.search(r'^[0-9]+-[0-9]+\u8282', text):
        return True
    if re.search(r'^\d{1,2}:\d{2}', text):
        return True
    return False


def _parse_day(text):
    mapping = {
        '\u5468\u4e00': 'Monday', '\u5468\u4e8c': 'Tuesday', '\u5468\u4e09': 'Wednesday',
        '\u5468\u56db': 'Thursday', '\u5468\u4e94': 'Friday', '\u5468\u516d': 'Saturday', '\u5468\u65e5': 'Sunday',
        '\u661f\u671f\u4e00': 'Monday', '\u661f\u671f\u4e8c': 'Tuesday', '\u661f\u671f\u4e09': 'Wednesday',
        '\u661f\u671f\u56db': 'Thursday', '\u661f\u671f\u4e94': 'Friday', '\u661f\u671f\u516d': 'Saturday', '\u661f\u671f\u65e5': 'Sunday',
        '\u54681': 'Monday', '\u54682': 'Tuesday', '\u54683': 'Wednesday',
        '\u54684': 'Thursday', '\u54685': 'Friday', '\u54686': 'Saturday', '\u54687': 'Sunday',
    }
    for cn, en in mapping.items():
        if cn in text:
            return en
    en_mapping = {
        'monday': 'Monday', 'tuesday': 'Tuesday', 'wednesday': 'Wednesday',
        'thursday': 'Thursday', 'friday': 'Friday', 'saturday': 'Saturday', 'sunday': 'Sunday',
    }
    text_lower = text.lower()
    for en_key, en_val in en_mapping.items():
        if en_key in text_lower:
            return en_val
    return ""


def _strip_day_from_time(text):
    text = re.sub(r'\u5468[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u65e5\u672b1-7]', '', text)
    text = re.sub(r'\u661f\u671f[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u65e5]', '', text)
    text = re.sub(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', '', text, flags=re.IGNORECASE)
    return text.strip()


def create_shortcut(target, shortcut_path, working_dir=None, icon=None, description=""):
    try:
        ps_cmd = f"$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('{shortcut_path}'); $s.TargetPath = '{target}'; $s.WorkingDirectory = '{working_dir or ''}'; "
        if icon:
            ps_cmd += f"$s.IconLocation = '{icon},0'; "
        if description:
            ps_cmd += f"$s.Description = '{description}'; "
        ps_cmd += "$s.Save()"
        result = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_cmd], capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except Exception:
        return False


def get_desktop_path():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            return winreg.QueryValueEx(key, "Desktop")[0]
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Desktop")


def get_startmenu_path():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            return winreg.QueryValueEx(key, "Programs")[0]
    except Exception:
        return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, bg=CONTENT_BG, highlightthickness=0, borderwidth=0)
        self.v_scroll = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=CONTENT_BG)
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.canvas.configure(yscrollcommand=self.v_scroll.set)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.v_scroll.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self._bind_mousewheel(self)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._window, width=event.width)

    def _bind_mousewheel(self, widget):
        widget.bind('<MouseWheel>', self._on_mousewheel)
        widget.bind('<Enter>', lambda e: self._bind_mousewheel_recursive(self.inner))
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    def _bind_mousewheel_recursive(self, widget):
        widget.bind('<MouseWheel>', self._on_mousewheel)
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} \u5b89\u88c5\u7a0b\u5e8f")
        self.root.geometry("880x640")
        self.root.minsize(800, 560)
        self.root.configure(bg=CONTENT_BG)

        self.source_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        self.app_exe = self.source_dir / APP_EXE_NAME

        self.current_step = 0
        self.total_steps = 7
        self.step_names = ["欢迎", "许可协议", "安装路径", "组件选择", "初始配置", "数据源选择", "安装"]

        self.install_dir = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.create_desktop_shortcut = tk.BooleanVar(value=True)
        self.create_startmenu_shortcut = tk.BooleanVar(value=True)
        self.setup_scheduler = tk.BooleanVar(value=True)
        self.launch_after_install = tk.BooleanVar(value=True)
        self.license_agreed = tk.BooleanVar(value=False)
        self.school_var = tk.StringVar()
        self.grade_var = tk.StringVar()
        self.semester_var = tk.StringVar()
        self.schedule_method = tk.StringVar(value='skip')
        self.schedule_file_path = tk.StringVar()
        self.interest_vars = {}

        now = datetime.now()
        sem = "\u6625\u590f" if 2 <= now.month <= 7 else "\u79cb\u51ac"
        self.semester_var.set(f"{now.year-1}-{now.year}\u5b66\u5e74{sem}\u5b66\u671f")

        self._build_ui()
        self._show_step(0)

    def _build_ui(self):
        self.sidebar = tk.Frame(self.root, bg=SIDEBAR_BG, width=180)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        logo_frame = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        logo_frame.pack(fill='x', pady=(25, 15))
        tk.Label(logo_frame, text="\U0001f4da", font=('Segoe UI Emoji', 28), bg=SIDEBAR_BG, fg=SIDEBAR_FG).pack()
        tk.Label(logo_frame, text=APP_NAME, font=('Microsoft YaHei', 12, 'bold'), bg=SIDEBAR_BG, fg=SIDEBAR_FG).pack(pady=(5, 0))
        tk.Label(logo_frame, text="\u5b89\u88c5\u5411\u5bfc", font=('Microsoft YaHei', 9), bg=SIDEBAR_BG, fg="#95a5a6").pack()

        self.step_labels = []
        for i, name in enumerate(self.step_names):
            f = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
            f.pack(fill='x', padx=10, pady=3)
            indicator = tk.Label(f, text="\u25cb", font=('Segoe UI', 12), bg=SIDEBAR_BG, fg="#7f8c8d", width=2)
            indicator.pack(side='left')
            lbl = tk.Label(f, text=name, font=('Microsoft YaHei', 10), bg=SIDEBAR_BG, fg="#7f8c8d", anchor='w')
            lbl.pack(side='left', fill='x')
            self.step_labels.append((indicator, lbl))

        tk.Frame(self.sidebar, bg=SIDEBAR_BG).pack(fill='both', expand=True)
        tk.Label(self.sidebar, text="v1.0.0", font=('Microsoft YaHei', 8), bg=SIDEBAR_BG, fg="#7f8c8d").pack(side='bottom', pady=10)

        right_frame = tk.Frame(self.root, bg=CONTENT_BG)
        right_frame.pack(side='right', fill='both', expand=True)

        self.bottom_frame = tk.Frame(right_frame, bg=CONTENT_BG)
        self.bottom_frame.pack(side='bottom', fill='x', padx=30, pady=(0, 20))
        tk.Frame(self.bottom_frame, bg=BORDER, height=1).pack(fill='x', pady=(0, 15))
        btn_container = tk.Frame(self.bottom_frame, bg=CONTENT_BG)
        btn_container.pack(fill='x')

        self.cancel_btn = tk.Button(btn_container, text="\u53d6\u6d88", font=('Microsoft YaHei', 10), bg="#ecf0f1", fg="#2c3e50", relief='flat', padx=20, pady=6, activebackground="#bdc3c7", cursor='hand2', command=self._on_cancel)
        self.cancel_btn.pack(side='left')
        self.back_btn = tk.Button(btn_container, text="\u25c0 \u4e0a\u4e00\u6b65", font=('Microsoft YaHei', 10), bg="#ecf0f1", fg="#2c3e50", relief='flat', padx=20, pady=6, activebackground="#bdc3c7", cursor='hand2', command=self._prev_step, state='disabled')
        self.back_btn.pack(side='right', padx=(10, 0))
        self.next_btn = tk.Button(btn_container, text="\u4e0b\u4e00\u6b65 \u25b6", font=('Microsoft YaHei', 10), bg=ACCENT, fg="white", relief='flat', padx=20, pady=6, activebackground=ACCENT_HOVER, cursor='hand2', command=self._next_step)
        self.next_btn.pack(side='right')

        self.content_frame = tk.Frame(right_frame, bg=CONTENT_BG)
        self.content_frame.pack(fill='both', expand=True, padx=30, pady=20)

    def _update_sidebar(self):
        for i, (indicator, lbl) in enumerate(self.step_labels):
            if i < self.current_step:
                indicator.config(text="\u25cf", fg=SIDEBAR_DONE); lbl.config(fg=SIDEBAR_DONE)
            elif i == self.current_step:
                indicator.config(text="\u25cf", fg=SIDEBAR_ACTIVE); lbl.config(fg=SIDEBAR_ACTIVE, font=('Microsoft YaHei', 10, 'bold'))
            else:
                indicator.config(text="\u25cb", fg="#7f8c8d"); lbl.config(fg="#7f8c8d", font=('Microsoft YaHei', 10))

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _show_step(self, step):
        self.current_step = step
        self._clear_content()
        self._update_sidebar()

        builders = [self._build_welcome, self._build_license, self._build_install_path, self._build_components, self._build_config, self._build_source_selection, self._build_installing]
        builders[step]()

        self.back_btn.config(state='normal' if step > 0 else 'disabled')
        self.cancel_btn.config(state='normal')

        if step == 6:
            self.next_btn.config(text="\u5b8c\u6210", state='disabled')
            self.cancel_btn.config(state='disabled')
            self.back_btn.config(state='disabled')
        elif step == 1 and not self.license_agreed.get():
            self.next_btn.config(text="\u4e0b\u4e00\u6b65 \u25b6", state='disabled')
        else:
            self.next_btn.config(text="\u4e0b\u4e00\u6b65 \u25b6", state='normal')

    def _build_welcome(self):
        sf = ScrollableFrame(self.content_frame)
        sf.pack(fill='both', expand=True)
        f = sf.inner

        tk.Label(f, text="\U0001f389", font=('Segoe UI Emoji', 36), bg=CONTENT_BG).pack(pady=(10, 5))
        tk.Label(f, text=f"\u6b22\u8fce\u5b89\u88c5 {APP_NAME}", font=('Microsoft YaHei', 18, 'bold'), bg=CONTENT_BG, fg="#2c3e50").pack()
        tk.Label(f, text="\u5b66\u672f\u81ea\u52a8\u5316\u52a9\u624b \u2014 \u8ba9\u4fe1\u606f\u627e\u4e0a\u95e8", font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#7f8c8d").pack(pady=(3, 15))

        features = [
            ("\U0001f4f0 \u5b66\u672f\u7b80\u62a5", "\u6bcf\u65e5\u81ea\u52a8\u6293\u53d6arXiv\u7b49\u5b66\u672f\u8d44\u8baf"),
            ("\U0001f4c5 \u8bfe\u7a0b\u63d0\u9192", "\u667a\u80fd\u8bfe\u8868\u7ba1\u7406\uff0c\u81ea\u52a8\u751f\u6210\u5b66\u4e60\u8ba1\u5212"),
            ("\U0001f4e7 \u90ae\u4ef6\u63a8\u9001", "\u81ea\u52a8\u53d1\u9001\u5b66\u672f\u7b80\u62a5\u5230\u4f60\u7684\u90ae\u7bb1"),
            ("\U0001f50d \u79bb\u7ebf\u4f18\u5148", "\u65e0\u9700\u8054\u7f51\uff0c\u53cc\u51fb\u5373\u7528"),
        ]
        grid = tk.Frame(f, bg=CONTENT_BG)
        grid.pack(pady=5)
        for i, (title, desc) in enumerate(features):
            card = tk.Frame(grid, bg="#f8f9fa", highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=i // 2, column=i % 2, padx=8, pady=5, sticky='nsew')
            tk.Label(card, text=title, font=('Microsoft YaHei', 10, 'bold'), bg="#f8f9fa", fg="#2c3e50").pack(pady=(8, 2))
            tk.Label(card, text=desc, font=('Microsoft YaHei', 9), bg="#f8f9fa", fg="#7f8c8d", wraplength=180).pack(pady=(0, 8))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        if not self.app_exe.exists():
            tk.Label(f, text=f"\u26a0\ufe0f \u672a\u627e\u5230 {APP_EXE_NAME}\uff0c\u8bf7\u786e\u4fdd\u5b89\u88c5\u7a0b\u5e8f\u4e0e\u4e3b\u7a0b\u5e8f\u5728\u540c\u4e00\u76ee\u5f55", font=('Microsoft YaHei', 9), bg=CONTENT_BG, fg="#e74c3c").pack(pady=(10, 0))

    def _build_license(self):
        f = self.content_frame

        agree_frame = tk.Frame(f, bg=CONTENT_BG)
        agree_frame.pack(side='bottom', fill='x', pady=(10, 0))
        tk.Checkbutton(agree_frame, text="\u2611 \u6211\u5df2\u9605\u8bfb\u5e76\u540c\u610f\u4ee5\u4e0a\u534f\u8bae", variable=self.license_agreed, font=('Microsoft YaHei', 11), bg=CONTENT_BG, fg="#2c3e50", activebackground=CONTENT_BG, selectcolor=CONTENT_BG, cursor='hand2', command=self._on_license_toggle).pack(anchor='w')

        tk.Label(f, text="\U0001f4dc \u8bb8\u53ef\u534f\u8bae", font=('Microsoft YaHei', 16, 'bold'), bg=CONTENT_BG, fg="#2c3e50").pack(anchor='w', pady=(0, 10))

        text_frame = tk.Frame(f, bg=CONTENT_BG)
        text_frame.pack(fill='both', expand=True)

        text_widget = tk.Text(text_frame, wrap='word', font=('Microsoft YaHei', 10), bg="#f8f9fa", fg="#2c3e50", relief='flat', padx=15, pady=15, highlightbackground=BORDER, highlightthickness=1)
        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        text_widget.pack(fill='both', expand=True)

        license_text = (
            f"{APP_NAME} \u4f7f\u7528\u8bb8\u53ef\u534f\u8bae\n\n"
            "\u7248\u6743\u58f0\u660e\n"
            f"{APP_NAME} \u662f\u514d\u8d39\u5f00\u6e90\u8f6f\u4ef6\uff0c\u4f9b\u4e2a\u4eba\u5b66\u4e60\u548c\u7814\u7a76\u4f7f\u7528\u3002\n\n"
            "\u4f7f\u7528\u6761\u6b3e\n"
            "1. \u672c\u8f6f\u4ef6\u6309\u201c\u539f\u6837\u201d\u63d0\u4f9b\uff0c\u4e0d\u63d0\u4f9b\u4efb\u4f55\u660e\u786e\u6216\u6697\u542b\u7684\u4fdd\u8bc1\u3002\n"
            "2. \u7528\u6237\u53ef\u81ea\u7531\u4f7f\u7528\u3001\u590d\u5236\u548c\u5206\u53d1\u672c\u8f6f\u4ef6\u3002\n"
            "3. \u7981\u6b62\u5c06\u672c\u8f6f\u4ef6\u7528\u4e8e\u5546\u4e1a\u8f6c\u552e\u3002\n"
            "4. \u4f7f\u7528\u672c\u8f6f\u4ef6\u4ea7\u751f\u7684\u4efb\u4f55\u95ee\u9898\uff0c\u5f00\u53d1\u8005\u4e0d\u627f\u62c5\u8d23\u4efb\u3002\n\n"
            "\u9690\u79c1\u58f0\u660e\n"
            "\u672c\u8f6f\u4ef6\u4e0d\u6536\u96c6\u3001\u4e0d\u4e0a\u4f20\u4efb\u4f55\u7528\u6237\u6570\u636e\u3002\u6240\u6709\u914d\u7f6e\u4ec5\u5b58\u50a8\u5728\u672c\u5730\u3002\n"
        )
        text_widget.insert('1.0', license_text)
        text_widget.config(state='disabled')

    def _on_license_toggle(self):
        self.next_btn.config(state='normal' if self.license_agreed.get() else 'disabled')

    def _build_install_path(self):
        f = self.content_frame
        tk.Label(f, text="\U0001f4c1 \u9009\u62e9\u5b89\u88c5\u8def\u5f84", font=('Microsoft YaHei', 16, 'bold'), bg=CONTENT_BG, fg="#2c3e50").pack(anchor='w', pady=(0, 5))
        tk.Label(f, text="\u9009\u62e9\u7a0b\u5e8f\u7684\u5b89\u88c5\u76ee\u5f55", font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#7f8c8d").pack(anchor='w', pady=(0, 15))

        path_frame = tk.Frame(f, bg=CONTENT_BG)
        path_frame.pack(fill='x', pady=5)
        tk.Entry(path_frame, textvariable=self.install_dir, font=('Microsoft YaHei', 11), relief='flat', bg="#f8f9fa", fg="#2c3e50", highlightbackground=BORDER, highlightthickness=1, insertbackground="#2c3e50").pack(side='left', fill='x', expand=True, ipady=8, padx=(0, 10))
        tk.Button(path_frame, text="\u6d4f\u89c8...", font=('Microsoft YaHei', 10), bg="#ecf0f1", fg="#2c3e50", relief='flat', padx=15, pady=6, activebackground="#bdc3c7", cursor='hand2', command=self._browse_dir).pack(side='right')

        info_frame = tk.Frame(f, bg="#f8f9fa", highlightbackground=BORDER, highlightthickness=1)
        info_frame.pack(fill='x', pady=15)
        try:
            drive = os.path.splitdrive(self.install_dir.get())[0] or "C:"
            usage = shutil.disk_usage(drive)
            disk_info = f"\u76d8\u7b26: {drive}  |  \u603b\u7a7a\u95f4: {usage.total/1024**3:.1f} GB  |  \u53ef\u7528: {usage.free/1024**3:.1f} GB"
        except Exception:
            disk_info = "\u65e0\u6cd5\u83b7\u53d6\u78c1\u76d8\u4fe1\u606f"
        tk.Label(info_frame, text="\u78c1\u76d8\u4fe1\u606f", font=('Microsoft YaHei', 10, 'bold'), bg="#f8f9fa", fg="#2c3e50").pack(anchor='w', padx=15, pady=(10, 5))
        tk.Label(info_frame, text=disk_info, font=('Microsoft YaHei', 9), bg="#f8f9fa", fg="#7f8c8d", justify='left').pack(anchor='w', padx=15, pady=(0, 10))

        tk.Label(f, text="\u9884\u8ba1\u6240\u9700\u7a7a\u95f4: ~50 MB", font=('Microsoft YaHei', 9), bg=CONTENT_BG, fg="#7f8c8d").pack(anchor='w')
        self.path_error = tk.Label(f, text="", font=('Microsoft YaHei', 9), bg=CONTENT_BG, fg="#e74c3c")
        self.path_error.pack(anchor='w', pady=(5, 0))

    def _browse_dir(self):
        directory = filedialog.askdirectory(initialdir=self.install_dir.get())
        if directory:
            self.install_dir.set(directory)

    def _build_components(self):
        f = self.content_frame
        tk.Label(f, text="\u2699\ufe0f \u7ec4\u4ef6\u9009\u62e9", font=('Microsoft YaHei', 16, 'bold'), bg=CONTENT_BG, fg="#2c3e50").pack(anchor='w', pady=(0, 5))
        tk.Label(f, text="\u9009\u62e9\u9700\u8981\u5b89\u88c5\u7684\u529f\u80fd\u7ec4\u4ef6", font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#7f8c8d").pack(anchor='w', pady=(0, 15))

        components = [
            (self.create_desktop_shortcut, "\U0001f5a5\ufe0f \u684c\u9762\u5feb\u6377\u65b9\u5f0f", "\u5728\u684c\u9762\u521b\u5efa\u7a0b\u5e8f\u5feb\u6377\u65b9\u5f0f"),
            (self.create_startmenu_shortcut, "\U0001f4cb \u5f00\u59cb\u83dc\u5355\u5feb\u6377\u65b9\u5f0f", "\u5728\u5f00\u59cb\u83dc\u5355\u6dfb\u52a0\u7a0b\u5e8f\u5feb\u6377\u65b9\u5f0f"),
            (self.setup_scheduler, "\u23f0 \u5b9a\u65f6\u4efb\u52a1", "\u8bbe\u7f6e\u6bcf\u65e5\u81ea\u52a8\u8fd0\u884c\uff0809:00 + 22:00\uff09"),
            (self.launch_after_install, "\U0001f680 \u5b89\u88c5\u540e\u542f\u52a8", "\u5b89\u88c5\u5b8c\u6210\u540e\u81ea\u52a8\u8fd0\u884c\u7a0b\u5e8f"),
        ]
        for var, title, desc in components:
            card = tk.Frame(f, bg="#f8f9fa", highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill='x', pady=4)
            cb_frame = tk.Frame(card, bg="#f8f9fa")
            cb_frame.pack(fill='x', padx=15, pady=10)
            tk.Checkbutton(cb_frame, variable=var, font=('Microsoft YaHei', 10), bg="#f8f9fa", fg="#2c3e50", activebackground="#f8f9fa", cursor='hand2').pack(side='left')
            text_frame = tk.Frame(cb_frame, bg="#f8f9fa")
            text_frame.pack(side='left', fill='x', expand=True, padx=(10, 0))
            tk.Label(text_frame, text=title, font=('Microsoft YaHei', 11, 'bold'), bg="#f8f9fa", fg="#2c3e50").pack(anchor='w')
            tk.Label(text_frame, text=desc, font=('Microsoft YaHei', 9), bg="#f8f9fa", fg="#7f8c8d").pack(anchor='w')

    def _build_config(self):
        sf = ScrollableFrame(self.content_frame)
        sf.pack(fill='both', expand=True)
        f = sf.inner

        tk.Label(f, text="\u2699\ufe0f \u521d\u59cb\u914d\u7f6e", font=('Microsoft YaHei', 16, 'bold'), bg=CONTENT_BG, fg="#2c3e50").pack(anchor='w', pady=(0, 5))
        tk.Label(f, text="\u914d\u7f6e\u4f60\u7684\u4e2a\u4eba\u4fe1\u606f\uff0c\u4e5f\u53ef\u4ee5\u8df3\u8fc7\u7a0d\u540e\u5728\u7a0b\u5e8f\u5185\u914d\u7f6e", font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#7f8c8d").pack(anchor='w', pady=(0, 10))

        basic_lf = tk.LabelFrame(f, text=" \U0001f4dd \u57fa\u672c\u4fe1\u606f ", font=('Microsoft YaHei', 11, 'bold'), bg=CONTENT_BG, fg="#2c3e50", padx=15, pady=10)
        basic_lf.pack(fill='x', pady=5)

        row1 = tk.Frame(basic_lf, bg=CONTENT_BG); row1.pack(fill='x', pady=6)
        tk.Label(row1, text="\u5b66\u6821:", font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#2c3e50", width=8).pack(side='left')
        self.school_combo = ttk.Combobox(row1, textvariable=self.school_var, values=POPULAR_SCHOOLS, width=25, font=('Microsoft YaHei', 10))
        self.school_combo.pack(side='left', padx=5)
        self.school_combo.bind('<<ComboboxSelected>>', self._on_school_select)
        self.school_entry = ttk.Entry(row1, width=25, font=('Microsoft YaHei', 10))
        self.school_entry.pack(side='left', padx=5); self.school_entry.pack_forget()

        row2 = tk.Frame(basic_lf, bg=CONTENT_BG); row2.pack(fill='x', pady=6)
        tk.Label(row2, text="\u5e74\u7ea7:", font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#2c3e50", width=8).pack(side='left')
        ttk.Combobox(row2, textvariable=self.grade_var, values=GRADES, width=23, state='readonly', font=('Microsoft YaHei', 10)).pack(side='left', padx=5)

        row3 = tk.Frame(basic_lf, bg=CONTENT_BG); row3.pack(fill='x', pady=6)
        tk.Label(row3, text="\u5b66\u671f:", font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#2c3e50", width=8).pack(side='left')
        ttk.Entry(row3, textvariable=self.semester_var, width=27, font=('Microsoft YaHei', 10)).pack(side='left', padx=5)

        schedule_lf = tk.LabelFrame(f, text=" \U0001f4c5 \u8bfe\u8868\u5bfc\u5165\uff08\u53ef\u8df3\u8fc7\uff09 ", font=('Microsoft YaHei', 11, 'bold'), bg=CONTENT_BG, fg="#2c3e50", padx=15, pady=10)
        schedule_lf.pack(fill='x', pady=8)

        method_frame = tk.Frame(schedule_lf, bg=CONTENT_BG); method_frame.pack(fill='x', pady=5)
        ttk.Radiobutton(method_frame, text="\u8df3\u8fc7", variable=self.schedule_method, value='skip').pack(side='left', padx=10)
        ttk.Radiobutton(method_frame, text="\U0001f4dd \u7c98\u8d34\u6587\u5b57", variable=self.schedule_method, value='text', command=self._toggle_schedule_input).pack(side='left', padx=10)
        ttk.Radiobutton(method_frame, text="\U0001f4c2 \u5bfc\u5165\u6587\u4ef6", variable=self.schedule_method, value='file', command=self._toggle_schedule_input).pack(side='left', padx=10)

        self.schedule_input_frame = tk.Frame(schedule_lf, bg=CONTENT_BG)
        self.schedule_text_widget = tk.Text(self.schedule_input_frame, height=5, width=55, font=('Microsoft YaHei', 9), bg="#f8f9fa", fg="#2c3e50", relief='flat', highlightbackground=BORDER, highlightthickness=1)
        self.schedule_text_widget.pack(fill='x', pady=5)
        tk.Label(self.schedule_input_frame, text="\u652f\u6301\u683c\u5f0f\uff1aTab/\u9017\u53f7/\u7ad6\u7ebf\u5206\u9694", font=('Microsoft YaHei', 8), bg=CONTENT_BG, fg="#95a5a6").pack(anchor='w')

        self.schedule_file_frame = tk.Frame(schedule_lf, bg=CONTENT_BG)
        file_row = tk.Frame(self.schedule_file_frame, bg=CONTENT_BG); file_row.pack(fill='x', pady=5)
        ttk.Entry(file_row, textvariable=self.schedule_file_path, width=40, font=('Microsoft YaHei', 10)).pack(side='left', padx=(0, 5))
        tk.Button(file_row, text="\u6d4f\u89c8...", font=('Microsoft YaHei', 9), bg="#ecf0f1", fg="#2c3e50", relief='flat', padx=10, pady=3, cursor='hand2', command=self._browse_schedule_file).pack(side='left')
        tk.Label(self.schedule_file_frame, text="\u652f\u6301 CSV / Excel (.xlsx)", font=('Microsoft YaHei', 8), bg=CONTENT_BG, fg="#95a5a6").pack(anchor='w')

        interest_lf = tk.LabelFrame(f, text=" \U0001f3af \u5174\u8da3\u65b9\u5411\uff08\u53ef\u591a\u9009\uff09 ", font=('Microsoft YaHei', 11, 'bold'), bg=CONTENT_BG, fg="#2c3e50", padx=15, pady=10)
        interest_lf.pack(fill='x', pady=8)
        tags_frame = tk.Frame(interest_lf, bg=CONTENT_BG); tags_frame.pack(fill='x', pady=5)
        self.interest_vars = {}
        for i, (name, _, _) in enumerate(INTEREST_AREAS):
            var = tk.BooleanVar(value=False)
            self.interest_vars[name] = var
            tk.Checkbutton(tags_frame, text=name, variable=var, font=('Microsoft YaHei', 9), bg=CONTENT_BG, fg="#2c3e50", activebackground=CONTENT_BG, cursor='hand2').grid(row=i // 3, column=i % 3, sticky='w', padx=5, pady=3)

    def _on_school_select(self, event):
        if self.school_var.get() == "\u5176\u4ed6\uff08\u624b\u52a8\u8f93\u5165\uff09":
            self.school_combo.pack_forget(); self.school_entry.pack(side='left', padx=5); self.school_entry.focus_set()
        else:
            self.school_entry.pack_forget(); self.school_combo.pack(side='left', padx=5)

    def _toggle_schedule_input(self):
        self.schedule_input_frame.pack_forget(); self.schedule_file_frame.pack_forget()
        if self.schedule_method.get() == 'text':
            self.schedule_input_frame.pack(fill='x', pady=5)
        elif self.schedule_method.get() == 'file':
            self.schedule_file_frame.pack(fill='x', pady=5)

    def _browse_schedule_file(self):
        filetypes = [("\u8868\u683c\u6587\u4ef6", "*.csv *.xlsx *.xls"), ("CSV", "*.csv"), ("Excel", "*.xlsx *.xls"), ("\u6240\u6709", "*.*")]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.schedule_file_path.set(filename)

    def _build_source_selection(self):
        sf = ScrollableFrame(self.content_frame)
        sf.pack(fill='both', expand=True)
        f = sf.inner

        tk.Label(f, text="数据源选择", font=('Microsoft YaHei', 16, 'bold'), bg=CONTENT_BG, fg="#2c3e50").pack(anchor='w', pady=(0, 5))
        tk.Label(f, text="选择你关注的学术数据源（取消勾选可大幅减少运行时间）", font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#7f8c8d").pack(anchor='w', pady=(0, 10))

        btn_frame = tk.Frame(f, bg=CONTENT_BG)
        btn_frame.pack(fill='x', pady=5)
        tk.Button(btn_frame, text="全选", font=('Microsoft YaHei', 9), bg="#ecf0f1", fg="#2c3e50", relief='flat', padx=10, pady=3, cursor='hand2', command=lambda: self._set_all_sources(True)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="全不选", font=('Microsoft YaHei', 9), bg="#ecf0f1", fg="#2c3e50", relief='flat', padx=10, pady=3, cursor='hand2', command=lambda: self._set_all_sources(False)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="推荐配置", font=('Microsoft YaHei', 9), bg="#3498db", fg="white", relief='flat', padx=10, pady=3, cursor='hand2', command=self._set_recommended_sources).pack(side='left', padx=5)

        self.source_vars = {}
        current_category = None

        for source in DEFAULT_NEWS_SOURCES:
            cat_key = source.get('category', 'general_academic')
            cat_name = SOURCE_CATEGORIES.get(cat_key, cat_key)

            if cat_key != current_category:
                current_category = cat_key
                cat_label = tk.Label(f, text=f"  {cat_name}", font=('Microsoft YaHei', 11, 'bold'), bg=CONTENT_BG, fg="#2c5f8a")
                cat_label.pack(anchor='w', padx=5, pady=(8, 2))
                ttk.Separator(f, orient='horizontal').pack(fill='x', padx=5, pady=1)

            row_frame = tk.Frame(f, bg=CONTENT_BG)
            row_frame.pack(fill='x', padx=15, pady=1)

            var = tk.BooleanVar(value=source.get('enabled', True))
            self.source_vars[source['name']] = var

            cb = tk.Checkbutton(row_frame, text=source['name'], variable=var, font=('Microsoft YaHei', 9), bg=CONTENT_BG, fg="#2c3e50", activebackground=CONTENT_BG, cursor='hand2')
            cb.pack(side='left')

            desc = source.get('desc', '')
            if desc:
                desc_label = tk.Label(row_frame, text=f"  - {desc}", foreground='gray', font=('Microsoft YaHei', 8), bg=CONTENT_BG)
                desc_label.pack(side='left', padx=(5, 0))

            type_tag = source.get('type', 'web').upper()
            type_label = tk.Label(row_frame, text=f"[{type_tag}]", foreground='#888', font=('Consolas', 8), bg=CONTENT_BG)
            type_label.pack(side='right', padx=5)

    def _set_all_sources(self, value):
        if hasattr(self, 'source_vars'):
            for var in self.source_vars.values():
                var.set(value)

    def _set_recommended_sources(self):
        if hasattr(self, 'source_vars'):
            for name, var in self.source_vars.items():
                default = next((s['enabled'] for s in DEFAULT_NEWS_SOURCES if s['name'] == name), True)
                var.set(default)

    def _build_installing(self):
        f = self.content_frame
        tk.Label(f, text="\U0001f4e6 \u6b63\u5728\u5b89\u88c5...", font=('Microsoft YaHei', 16, 'bold'), bg=CONTENT_BG, fg="#2c3e50").pack(anchor='w', pady=(0, 10))
        self.progress = ttk.Progressbar(f, mode='determinate', length=560)
        self.progress.pack(fill='x', pady=(0, 8))
        self.status_label = tk.Label(f, text="\u51c6\u5907\u5b89\u88c5...", font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#7f8c8d")
        self.status_label.pack(anchor='w')
        self.log_text = tk.Text(f, height=14, width=65, font=('Consolas', 9), bg="#f8f9fa", fg="#2c3e50", relief='flat', highlightbackground=BORDER, highlightthickness=1)
        self.log_text.pack(fill='both', expand=True, pady=(8, 0))
        self.log_text.config(state='disabled')
        self._install_done = False
        self.root.after(300, self._do_install)

    def _log(self, msg):
        self.log_text.config(state='normal'); self.log_text.insert('end', msg + '\n'); self.log_text.see('end'); self.log_text.config(state='disabled'); self.root.update_idletasks()

    def _set_progress(self, value, status=""):
        self.progress['value'] = value
        if status:
            self.status_label.config(text=status)
        self.root.update_idletasks()

    def _do_install(self):
        install_dir = Path(self.install_dir.get())
        try:
            self._set_progress(5, "\u521b\u5efa\u5b89\u88c5\u76ee\u5f55...")
            self._log(f"\u2713 \u521b\u5efa\u76ee\u5f55: {install_dir}")
            install_dir.mkdir(parents=True, exist_ok=True)
            (install_dir / "data").mkdir(exist_ok=True)
            (install_dir / "logs").mkdir(exist_ok=True)

            self._set_progress(15, "\u590d\u5236\u7a0b\u5e8f\u6587\u4ef6...")
            if self.app_exe.exists():
                shutil.copy2(str(self.app_exe), str(install_dir / APP_EXE_NAME))
                self._log(f"\u2713 \u590d\u5236: {APP_EXE_NAME}")
            else:
                self._log(f"\u26a0 \u672a\u627e\u5230 {APP_EXE_NAME}\uff0c\u8df3\u8fc7")

            self._set_progress(25, "\u590d\u5236\u8f85\u52a9\u6587\u4ef6...")
            for fname in ["run_daily.bat", "run_schedule.bat", "run_all_morning.bat", "setup_task_scheduler.bat"]:
                src = self.source_dir / fname
                if src.exists():
                    shutil.copy2(str(src), str(install_dir / fname))
                    self._log(f"\u2713 \u590d\u5236: {fname}")

            self._set_progress(40, "\u521b\u5efa\u9ed8\u8ba4\u914d\u7f6e...")
            self._create_default_config(install_dir)
            self._log("\u2713 \u914d\u7f6e\u6587\u4ef6\u5df2\u521b\u5efa")

            self._set_progress(55, "\u4fdd\u5b58\u521d\u59cb\u914d\u7f6e...")
            self._save_user_config(install_dir)
            self._log("\u2713 \u7528\u6237\u914d\u7f6e\u5df2\u4fdd\u5b58")

            if self.create_desktop_shortcut.get():
                self._set_progress(65, "\u521b\u5efa\u684c\u9762\u5feb\u6377\u65b9\u5f0f...")
                target = str(install_dir / APP_EXE_NAME)
                if create_shortcut(target, os.path.join(get_desktop_path(), f"{APP_NAME}.lnk"), str(install_dir), target, APP_NAME):
                    self._log("\u2713 \u684c\u9762\u5feb\u6377\u65b9\u5f0f\u5df2\u521b\u5efa")
                else:
                    self._log("\u26a0 \u684c\u9762\u5feb\u6377\u65b9\u5f0f\u521b\u5efa\u5931\u8d25")

            if self.create_startmenu_shortcut.get():
                self._set_progress(72, "\u521b\u5efa\u5f00\u59cb\u83dc\u5355...")
                startmenu = get_startmenu_path()
                app_folder = os.path.join(startmenu, APP_NAME)
                os.makedirs(app_folder, exist_ok=True)
                target = str(install_dir / APP_EXE_NAME)
                if create_shortcut(target, os.path.join(app_folder, f"{APP_NAME}.lnk"), str(install_dir), target, APP_NAME):
                    self._log("\u2713 \u5f00\u59cb\u83dc\u5355\u5feb\u6377\u65b9\u5f0f\u5df2\u521b\u5efa")
                else:
                    self._log("\u26a0 \u5f00\u59cb\u83dc\u5355\u5feb\u6377\u65b9\u5f0f\u521b\u5efa\u5931\u8d25")

            if self.setup_scheduler.get():
                self._set_progress(82, "\u8bbe\u7f6e\u5b9a\u65f6\u4efb\u52a1...")
                self._setup_scheduled_tasks(install_dir)

            self._set_progress(92, "\u8bbe\u7f6e\u6587\u4ef6\u6743\u9650...")
            try:
                subprocess.run(['icacls', str(install_dir), '/grant', 'Users:(OI)(CI)F', '/T'], capture_output=True, timeout=10)
                self._log("\u2713 \u6587\u4ef6\u6743\u9650\u5df2\u8bbe\u7f6e")
            except Exception:
                self._log("\u26a0 \u6587\u4ef6\u6743\u9650\u8bbe\u7f6e\u8df3\u8fc7")

            self._set_progress(100, "\u5b89\u88c5\u5b8c\u6210!")
            self._log("\n" + "=" * 50)
            self._log(f"\u2713 {APP_NAME} \u5b89\u88c5\u5b8c\u6210!")
            self._log(f"  \u5b89\u88c5\u76ee\u5f55: {install_dir}")

            self._install_done = True
            self.next_btn.config(text="\u5b8c\u6210", state='normal')
            self.cancel_btn.config(state='normal')
            self._clear_content()
            self._build_complete(install_dir)
        except Exception as e:
            self._log(f"\n\u2717 \u5b89\u88c5\u5931\u8d25: {e}")
            self._set_progress(0, f"\u5b89\u88c5\u5931\u8d25: {e}")
            self.next_btn.config(state='normal')
            self.cancel_btn.config(state='normal')

    def _create_default_config(self, install_dir):
        default_config = {
            "news_sources": DEFAULT_NEWS_SOURCES,
            "reminders": [
                {"time": "09:00", "title": "学术早报", "description": "今日最新学术资讯已整理完毕，请查阅。"},
                {"time": "22:00", "title": "晚间复盘", "description": "今日工作告一段落，回顾一下收获。"}
            ],
            "keywords": ["artificial intelligence", "machine learning", "big data", "public governance", "digital governance"],
            "keywords_cn": ["人工智能", "大数据", "公共治理", "数字治理"],
            "output_format": "markdown",
            "translation": {"enabled": False, "target_lang": "en"},
            "max_items_per_source": 5,
            "email": {"enabled": False, "smtp_server": "smtp.qq.com", "smtp_port": 587, "sender_email": "", "sender_password": "", "receiver_email": "", "subject_prefix": "[学术简报]"},
            "api_keys": {"semantic_scholar": "", "openalex": "", "core": ""}
        }
        with open(install_dir / "config.json", 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        default_schedule = {
            "semester": self.semester_var.get().strip(),
            "week_schedule": {"Monday": [], "Tuesday": [], "Wednesday": [], "Thursday": [], "Friday": [], "Saturday": [], "Sunday": []},
            "review_tasks": {}, "daily_routine": {}
        }
        with open(install_dir / "schedule.json", 'w', encoding='utf-8') as f:
            json.dump(default_schedule, f, ensure_ascii=False, indent=2)

    def _save_user_config(self, install_dir):
        with open(install_dir / "config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        with open(install_dir / "schedule.json", 'r', encoding='utf-8') as f:
            schedule = json.load(f)
        en_kw = list(config.get('keywords', []))
        cn_kw = list(config.get('keywords_cn', []))
        for name, en_list, cn_list in INTEREST_AREAS:
            if self.interest_vars.get(name, tk.BooleanVar()).get():
                en_kw.extend(en_list); cn_kw.extend(cn_list)
        config['keywords'] = list(dict.fromkeys(en_kw))
        config['keywords_cn'] = list(dict.fromkeys(cn_kw))

        if hasattr(self, 'source_vars'):
            for source in config.get('news_sources', []):
                if source['name'] in self.source_vars:
                    source['enabled'] = self.source_vars[source['name']].get()

        with open(install_dir / "config.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        if self.schedule_method.get() == 'text' and hasattr(self, 'schedule_text_widget'):
            text = self.schedule_text_widget.get(1.0, tk.END).strip()
            if text:
                self._add_courses_to_schedule(schedule, parse_course_table(text))
        elif self.schedule_method.get() == 'file':
            fp = self.schedule_file_path.get().strip()
            if fp:
                courses = self._parse_schedule_file(fp)
                if courses:
                    self._add_courses_to_schedule(schedule, courses)
        with open(install_dir / "schedule.json", 'w', encoding='utf-8') as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)

    def _add_courses_to_schedule(self, schedule, courses):
        if 'week_schedule' not in schedule:
            schedule['week_schedule'] = {}
        for day in DAY_NAMES_EN:
            if day not in schedule['week_schedule']:
                schedule['week_schedule'][day] = []
        for c in courses:
            day = c['day']
            if day not in schedule['week_schedule']:
                schedule['week_schedule'][day] = []
            schedule['week_schedule'][day].append({'name': c['name'], 'time': c['time'], 'location': c['location'], 'teacher': c['teacher'], 'note': c.get('note', '')})

    def _parse_schedule_file(self, filepath):
        path = Path(filepath)
        if not path.exists():
            return []
        try:
            if path.suffix.lower() == '.csv':
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    rows = list(csv.reader(f))
                return parse_course_table('\n'.join(['\t'.join(row) for row in rows])) if rows else []
            elif path.suffix.lower() in ('.xlsx', '.xls'):
                try:
                    import openpyxl
                except ImportError:
                    return []
                wb = openpyxl.load_workbook(path, read_only=True)
                rows = [[str(c) if c is not None else '' for c in row] for row in wb.active.iter_rows(values_only=True)]
                wb.close()
                return parse_course_table('\n'.join(['\t'.join(row) for row in rows])) if rows else []
            else:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    return parse_course_table(f.read())
        except Exception:
            return []

    def _setup_scheduled_tasks(self, install_dir):
        batch_path = str(install_dir / "run_daily.bat")
        for task_name in ["DailyAutomation_Morning", "DailyAutomation_Evening"]:
            try:
                subprocess.run(['schtasks', '/delete', '/tn', task_name, '/f'], capture_output=True, timeout=10)
            except Exception:
                pass
        try:
            subprocess.run(['schtasks', '/create', '/tn', 'DailyAutomation_Morning', '/tr', f'"{batch_path}"', '/sc', 'daily', '/st', '09:00', '/ru', os.getenv('USERNAME'), '/f'], capture_output=True, timeout=15)
            self._log("  \u2713 \u65e9\u6668\u4efb\u52a1 (09:00)")
        except Exception as e:
            self._log(f"  \u26a0 \u65e9\u6668\u4efb\u52a1\u521b\u5efa\u5931\u8d25: {e}")
        try:
            subprocess.run(['schtasks', '/create', '/tn', 'DailyAutomation_Evening', '/tr', f'"{batch_path}" remind', '/sc', 'daily', '/st', '22:00', '/ru', os.getenv('USERNAME'), '/f'], capture_output=True, timeout=15)
            self._log("  \u2713 \u665a\u95f4\u4efb\u52a1 (22:00)")
        except Exception as e:
            self._log(f"  \u26a0 \u665a\u95f4\u4efb\u52a1\u521b\u5efa\u5931\u8d25: {e}")

    def _build_complete(self, install_dir):
        f = self.content_frame
        tk.Label(f, text="\u2705", font=('Segoe UI Emoji', 48), bg=CONTENT_BG).pack(pady=(15, 10))
        tk.Label(f, text="\u5b89\u88c5\u5b8c\u6210!", font=('Microsoft YaHei', 22, 'bold'), bg=CONTENT_BG, fg="#27ae60").pack()
        tk.Label(f, text=f"{APP_NAME} \u5df2\u6210\u529f\u5b89\u88c5\u5230\u60a8\u7684\u7535\u8111", font=('Microsoft YaHei', 11), bg=CONTENT_BG, fg="#7f8c8d").pack(pady=(5, 20))

        summary_frame = tk.Frame(f, bg="#f8f9fa", highlightbackground=BORDER, highlightthickness=1)
        summary_frame.pack(fill='x', padx=20, pady=5)
        for icon_label, value in [
            ("\U0001f4c1 \u5b89\u88c5\u76ee\u5f55", str(install_dir)),
            ("\U0001f5a5\ufe0f \u684c\u9762\u5feb\u6377\u65b9\u5f0f", "\u5df2\u521b\u5efa" if self.create_desktop_shortcut.get() else "\u672a\u521b\u5efa"),
            ("\U0001f4cb \u5f00\u59cb\u83dc\u5355", "\u5df2\u521b\u5efa" if self.create_startmenu_shortcut.get() else "\u672a\u521b\u5efa"),
            ("\u23f0 \u5b9a\u65f6\u4efb\u52a1", "\u5df2\u8bbe\u7f6e" if self.setup_scheduler.get() else "\u672a\u8bbe\u7f6e"),
        ]:
            row = tk.Frame(summary_frame, bg="#f8f9fa"); row.pack(fill='x', padx=15, pady=6)
            tk.Label(row, text=icon_label, font=('Microsoft YaHei', 10), bg="#f8f9fa", fg="#2c3e50", width=12, anchor='w').pack(side='left')
            tk.Label(row, text=value, font=('Microsoft YaHei', 10), bg="#f8f9fa", fg="#7f8c8d", anchor='w').pack(side='left', fill='x', expand=True)

        self.launch_var = tk.BooleanVar(value=self.launch_after_install.get())
        launch_frame = tk.Frame(f, bg=CONTENT_BG); launch_frame.pack(fill='x', padx=20, pady=(20, 0))
        tk.Checkbutton(launch_frame, text="\u7acb\u5373\u542f\u52a8 Daily Automation", variable=self.launch_var, font=('Microsoft YaHei', 10), bg=CONTENT_BG, fg="#2c3e50", activebackground=CONTENT_BG, cursor='hand2').pack(anchor='w')

    def _next_step(self):
        if self.current_step == 5 and self._install_done:
            if self.launch_var.get():
                exe_path = Path(self.install_dir.get()) / APP_EXE_NAME
                if exe_path.exists():
                    os.startfile(str(exe_path))
            self.root.destroy()
            return
        if self.current_step == 1 and not self.license_agreed.get():
            return
        if self.current_step == 2:
            path = self.install_dir.get().strip()
            if not path:
                if hasattr(self, 'path_error'):
                    self.path_error.config(text="\u8bf7\u8f93\u5165\u5b89\u88c5\u8def\u5f84")
                return
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
                if not os.access(path, os.W_OK):
                    if hasattr(self, 'path_error'):
                        self.path_error.config(text="\u6ca1\u6709\u5199\u5165\u6743\u9650\uff0c\u8bf7\u9009\u62e9\u5176\u4ed6\u76ee\u5f55")
                    return
            except Exception as e:
                if hasattr(self, 'path_error'):
                    self.path_error.config(text=f"\u8def\u5f84\u65e0\u6548: {e}")
                return
        if self.current_step < self.total_steps - 1:
            self._show_step(self.current_step + 1)

    def _prev_step(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _on_cancel(self):
        if self.current_step == 5 and not self._install_done:
            return
        if messagebox.askyesno("\u53d6\u6d88\u5b89\u88c5", "\u786e\u5b9a\u8981\u53d6\u6d88\u5b89\u88c5\u5417\uff1f"):
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = InstallerApp()
    app.run()
