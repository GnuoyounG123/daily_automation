#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程任务管理系统 - Schedule & Task Manager
功能：课表管理、任务拆解、每日提醒
作者：Claude Code
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# ============ 配置区域 ============
CONFIG_DIR = Path(__file__).parent
DATA_DIR = CONFIG_DIR / "data"
LOG_DIR = CONFIG_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

SCHEDULE_FILE = CONFIG_DIR / "schedule.json"
TASKS_FILE = CONFIG_DIR / "weekly_tasks.json"


def log_message(message, level="INFO"):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    print(log_entry.strip())
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)


# ============ 温暖关心语录库 ============
ENCOURAGEMENTS = [
    "记得吃早餐哦，空腹上课对胃不好。",
    "今天天气可能有点凉，记得带件外套。",
    "昨晚睡得好吗？别太累着自己。",
    "如果今天觉得累了，就停下来歇一歇。",
    "不管今天发生什么，我都在这里陪着你。",
    "你的健康比任何作业都重要，记得按时吃饭。",
    "慢一点没关系，不用总是逼自己那么紧。",
    "今天的你已经很棒了，不需要证明什么。",
    "如果遇到困难，随时来找我，我帮你一起想办法。",
    "记得多喝水，坐久了起来活动活动。",
    "你的眼睛很珍贵，看屏幕久了记得望远休息。",
    "今天的任务如果太多，我们就挑最重要的做。",
    "不管做得怎么样，我都知道你已经很努力了。",
    "累了就早点休息，明天的事明天再说。",
    "你不用一直坚强，偶尔也可以示弱。",
    "我帮你记着这些事呢，不用担心会忘记。",
    "今天也要照顾好自己，其他的都不急。",
    "如果心情不好，就听听喜欢的歌吧。",
    "你已经做得很好了，真的。",
    "记得对自己温柔一点，像对待好朋友那样。"
]

MORNING_GREETINGS = [
    "早安，主人～",
    "早呀，今天也好好吃早餐了吗？",
    "主人醒啦，喵～",
    "早安，今天也要对自己好一点哦",
    "早上好，记得慢慢来，不着急的",
    "喵～早安呀"
]


def get_random_encouragement():
    """获取随机鼓励语"""
    return random.choice(ENCOURAGEMENTS)


def get_random_greeting():
    """获取随机问候语"""
    return random.choice(MORNING_GREETINGS)


# ============ 课表管理 ============

def load_schedule():
    """加载课表"""
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return create_default_schedule()


def create_default_schedule():
    """创建默认课表结构"""
    default = {
        "semester": "2024-2025学年春季学期",
        "courses": [],
        "class_time": {
            "1": {"start": "08:00", "end": "08:45"},
            "2": {"start": "08:55", "end": "09:40"},
            "3": {"start": "10:00", "end": "10:45"},
            "4": {"start": "10:55", "end": "11:40"},
            "5": {"start": "14:00", "end": "14:45"},
            "6": {"start": "14:55", "end": "15:40"},
            "7": {"start": "16:00", "end": "16:45"},
            "8": {"start": "16:55", "end": "17:40"},
            "9": {"start": "18:30", "end": "19:15"},
            "10": {"start": "19:25", "end": "20:10"}
        },
        "week_schedule": {
            "Monday": [],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": [],
            "Sunday": []
        }
    }
    save_schedule(default)
    return default


def save_schedule(schedule):
    """保存课表"""
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)


# ============ 任务管理 ============

def load_weekly_tasks():
    """加载本周任务"""
    if TASKS_FILE.exists():
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return create_empty_tasks()


def create_empty_tasks():
    """创建空任务结构"""
    return {
        "semester_goals": [],
        "this_week": {
            "big_tasks": [],
            "deadlines": [],
            "daily_breakdown": {}
        },
        "last_updated": datetime.now().isoformat()
    }


def save_weekly_tasks(tasks):
    """保存本周任务"""
    tasks["last_updated"] = datetime.now().isoformat()
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


# ============ 每日任务生成 ============

def get_today_schedule(schedule, daily_tasks):
    """获取今天的课表和任务"""
    # 获取今天是星期几
    weekday_map = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday"
    }

    today_weekday = datetime.now().weekday()
    today_name = weekday_map[today_weekday]
    today_date = datetime.now().strftime("%Y年%m月%d日")

    # 获取今天的课程
    today_courses = schedule.get("week_schedule", {}).get(today_name, [])

    # 获取今天的任务
    today_tasks = daily_tasks.get(today_name, [])

    return {
        "date": today_date,
        "weekday": today_name,
        "courses": today_courses,
        "tasks": today_tasks
    }


def generate_daily_plan(schedule, daily_tasks):
    """生成每日计划"""
    today_info = get_today_schedule(schedule, daily_tasks)

    greeting = get_random_greeting()
    encouragement = get_random_encouragement()

    # 生成HTML邮件
    html = generate_daily_html(today_info, greeting, encouragement)

    return html, today_info


def generate_daily_html(today_info, greeting, encouragement):
    """生成美观的每日计划HTML"""
    date = today_info["date"]
    weekday = today_info["weekday"]
    courses = today_info["courses"]
    tasks = today_info["tasks"]

    # 中文星期
    weekday_cn = {
        "Monday": "周一",
        "Tuesday": "周二",
        "Wednesday": "周三",
        "Thursday": "周四",
        "Friday": "周五",
        "Saturday": "周六",
        "Sunday": "周日"
    }

    # 课程HTML
    courses_html = ""
    if courses:
        for course in courses:
            courses_html += f"""
            <div class="course-item">
                <div class="course-time">{course.get('time', '')}</div>
                <div class="course-info">
                    <div class="course-name">{course.get('name', '')}</div>
                    <div class="course-location">📍 {course.get('location', '')}</div>
                </div>
            </div>
            """
    else:
        courses_html = '<div class="empty">今天没有课程，可以自由安排学习时间～</div>'

    # 任务HTML
    tasks_html = ""
    if tasks:
        for task in tasks:
            content = task.get("content", "")
            note = task.get("note", "")

            # 构建任务显示
            task_display = content
            if note:
                task_display += f"<br><span style='color:#888;font-size:13px;'>💡 {note}</span>"

            tasks_html += f"""
            <div class="task-item">
                <div class="task-content">{task_display}</div>
            </div>
            """
    else:
        tasks_html = '<div class="empty">今天没有额外任务，好好休息或者读点自己喜欢的书吧～</div>'

    # 完整HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>今日计划 - {date}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}

        .greeting {{
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .date {{
            font-size: 18px;
            opacity: 0.9;
            margin-bottom: 15px;
        }}

        .encouragement {{
            background: rgba(255,255,255,0.2);
            border-radius: 15px;
            padding: 15px 20px;
            font-size: 14px;
            line-height: 1.6;
            margin-top: 20px;
            font-style: italic;
        }}

        .content {{
            padding: 30px;
        }}

        .section {{
            margin-bottom: 30px;
        }}

        .section-title {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .section-icon {{
            font-size: 24px;
        }}

        .course-item {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            gap: 15px;
            align-items: center;
            border-left: 4px solid #667eea;
        }}

        .course-time {{
            background: #667eea;
            color: white;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            white-space: nowrap;
        }}

        .course-info {{
            flex: 1;
        }}

        .course-name {{
            font-size: 16px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}

        .course-location {{
            font-size: 13px;
            color: #666;
        }}

        .task-item {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #28a745;
        }}

        .task-item.priority-high {{
            border-left-color: #dc3545;
            background: #fff5f5;
        }}

        .task-item.priority-medium {{
            border-left-color: #ffc107;
            background: #fffbf0;
        }}

        .task-item.priority-low {{
            border-left-color: #28a745;
        }}

        .task-content {{
            font-size: 15px;
            color: #333;
            margin-bottom: 5px;
        }}

        .task-meta {{
            font-size: 12px;
            color: #888;
        }}

        .empty {{
            text-align: center;
            color: #999;
            padding: 30px;
            font-style: italic;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            color: #666;
            font-size: 13px;
        }}

        .footer .heart {{
            color: #e74c3c;
        }}

        .quote {{
            margin-top: 10px;
            font-style: italic;
            color: #888;
        }}

        @media (max-width: 600px) {{
            body {{
                padding: 10px;
            }}

            .header {{
                padding: 30px 20px;
            }}

            .greeting {{
                font-size: 24px;
            }}

            .content {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="greeting">{greeting}</div>
            <div class="date">{date} · {weekday_cn.get(weekday, weekday)}</div>
            <div class="encouragement">"{encouragement}"</div>
        </div>

        <div class="content">
            <div class="section">
                <div class="section-title">
                    <span class="section-icon">📚</span>
                    今日课程
                </div>
                {courses_html}
            </div>

            <div class="section">
                <div class="section-title">
                    <span class="section-icon">✨</span>
                    今日任务
                </div>
                {tasks_html}
            </div>
        </div>

        <div class="footer">
            <p>喵一直在这里陪着您 <span class="heart">♥</span></p>
            <p class="quote">"今天也要记得对自己好一点，其他的都不急。"</p>
        </div>
    </div>
</body>
</html>"""

    return html


# ============ 邮件发送 ============

def send_daily_email(html_content, config):
    """发送每日计划邮件"""
    if not config.get('enabled', False):
        log_message("邮件功能已禁用")
        return False

    try:
        msg = MIMEMultipart('alternative')
        today = datetime.now().strftime("%Y年%m月%d日")
        msg['Subject'] = Header(f"[今日计划] {today} 早安，主人！", 'utf-8')
        msg['From'] = config.get('sender_email', '')
        msg['To'] = config.get('receiver_email', '')

        # 添加HTML内容
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)

        # 连接SMTP
        smtp_server = config.get('smtp_server', 'smtp.qq.com')
        smtp_port = config.get('smtp_port', 587)

        log_message(f"正在发送邮件到 {config.get('receiver_email')}...")

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()

        server.login(config.get('sender_email'), config.get('sender_password'))
        server.sendmail(
            config.get('sender_email'),
            config.get('receiver_email'),
            msg.as_string()
        )
        server.quit()

        log_message("邮件发送成功！")
        return True

    except Exception as e:
        log_message(f"邮件发送失败: {str(e)}", "ERROR")
        return False


# ============ 主程序 ============

def main():
    """主程序入口"""
    log_message("="*60)
    log_message("课程任务管理系统启动")
    log_message("="*60)

    # 加载配置
    config_file = CONFIG_DIR / "config.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        log_message("未找到config.json，请确保配置文件存在", "ERROR")
        return

    # 加载课表和任务
    schedule = load_schedule()
    week_tasks = load_weekly_tasks()

    # 直接读取每日任务（由Claude手动配置）
    daily_tasks = week_tasks.get("daily_tasks", {})

    # 生成今日计划
    log_message("正在生成今日计划...")
    html_content, today_info = generate_daily_plan(schedule, daily_tasks)

    # 保存今日计划
    date_str = datetime.now().strftime("%Y%m%d")
    plan_file = DATA_DIR / f"daily_plan_{date_str}.html"
    with open(plan_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    log_message(f"今日计划已保存: {plan_file}")

    # 发送邮件
    email_config = config.get('email', {})
    if email_config.get('enabled', False):
        send_daily_email(html_content, email_config)
    else:
        log_message("邮件功能未启用，跳过发送")

    log_message("="*60)
    log_message("课程任务管理系统执行完毕")
    log_message("="*60)


if __name__ == "__main__":
    main()
