#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Automation 配置中心
Streamlit Web界面 - 让用户轻松配置学术自动化助手
"""

import streamlit as st
from pathlib import Path
import json
from datetime import datetime

from config_manager import ConfigManager

# ========== 页面配置 ==========
st.set_page_config(
    page_title="Daily Automation 配置中心",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 初始化 ==========
@st.cache_resource
def get_config_manager():
    return ConfigManager(Path(__file__).parent)

config_manager = get_config_manager()

# ========== 侧边栏导航 ==========
st.sidebar.title("📚 Daily Automation")
st.sidebar.caption("学术自动化助手配置中心")

page = st.sidebar.radio(
    "导航",
    ["🏠 首页", "📰 新闻源管理", "🔑 关键词设置", "⏰ 提醒管理", "📧 邮箱配置", "📅 课程表", "⚙️ 高级设置", "💾 导入导出"],
    label_visibility="collapsed"
)

st.sidebar.divider()

# ========== 首页 ==========
if page == "🏠 首页":
    st.title("📚 Daily Automation 配置中心")
    st.markdown("欢迎！这是您的学术自动化助手配置界面。")

    # 状态概览
    config = config_manager.get_config()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sources = config.get('news_sources', [])
        enabled_sources = [s for s in sources if s.get('enabled', True)]
        st.metric("新闻源", f"{len(enabled_sources)}/{len(sources)}")

    with col2:
        keywords = config.get('keywords', [])
        keywords_cn = config.get('keywords_cn', [])
        st.metric("关键词", f"{len(keywords) + len(keywords_cn)}")

    with col3:
        reminders = config.get('reminders', [])
        st.metric("提醒事项", len(reminders))

    with col4:
        email = config.get('email', {})
        st.metric("邮件状态", "已启用" if email.get('enabled') else "未启用")

    st.divider()

    # 快速操作
    st.subheader("🚀 快速操作")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ 立即运行一次", use_container_width=True):
            st.info("请在命令行运行: python daily_assistant.py")

    with col2:
        if st.button("🔄 重置为默认配置", use_container_width=True):
            config_manager.reset_to_default()
            st.success("已重置为默认配置")
            st.rerun()

    with col3:
        if st.button("📥 导出当前配置", use_container_width=True):
            data = config_manager.export_all_config()
            st.download_button(
                label="下载配置文件",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name=f"daily_automation_config_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

    st.divider()

    # 最近运行状态
    st.subheader("📊 最近状态")
    log_dir = Path(__file__).parent / "logs"
    if log_dir.exists():
        log_files = sorted(log_dir.glob("*.log"), key=lambda x: x.name, reverse=True)[:5]
        if log_files:
            for log_file in log_files:
                st.caption(f"📄 {log_file.name}")
        else:
            st.info("暂无运行记录")
    else:
        st.info("暂无运行记录")

# ========== 新闻源管理 ==========
elif page == "📰 新闻源管理":
    st.title("📰 新闻源管理")
    st.markdown("管理学术信息爬取来源")

    # 显示现有新闻源
    sources = config_manager.get_news_sources()

    if sources:
        st.subheader("当前新闻源")
        for i, source in enumerate(sources):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 4, 1, 1, 1])

                with col1:
                    new_name = st.text_input("名称", source['name'], key=f"name_{i}", label_visibility="collapsed")

                with col2:
                    new_url = st.text_input("URL", source['url'], key=f"url_{i}", label_visibility="collapsed")

                with col3:
                    new_type = st.selectbox(
                        "类型",
                        ["rss", "web", "json"],
                        index=["rss", "web", "json"].index(source.get('type', 'rss')),
                        key=f"type_{i}",
                        label_visibility="collapsed"
                    )

                with col4:
                    new_enabled = st.checkbox(
                        "启用",
                        source.get('enabled', True),
                        key=f"enabled_{i}",
                        label_visibility="collapsed"
                    )

                with col5:
                    if st.button("🗑️", key=f"delete_{i}", help="删除此新闻源"):
                        if config_manager.delete_news_source(i):
                            st.success("已删除")
                            st.rerun()

                # 更新按钮
                if st.button("💾 保存修改", key=f"save_{i}"):
                    config_manager.update_news_source(
                        i, name=new_name, url=new_url,
                        source_type=new_type, enabled=new_enabled
                    )
                    st.success("已保存")
                    st.rerun()

                st.divider()
    else:
        st.info("暂无新闻源，请添加")

    # 添加新新闻源
    st.subheader("➕ 添加新闻源")
    with st.form("add_source_form"):
        col1, col2 = st.columns(2)

        with col1:
            new_source_name = st.text_input("名称", placeholder="例如: arXiv AI")
            new_source_url = st.text_input("URL", placeholder="例如: http://export.arxiv.org/api/...")

        with col2:
            new_source_type = st.selectbox("类型", ["rss", "web", "json"])
            new_source_enabled = st.checkbox("启用", value=True)

        submitted = st.form_submit_button("添加新闻源", use_container_width=True)
        if submitted:
            if new_source_name and new_source_url:
                if config_manager.add_news_source(new_source_name, new_source_url, new_source_type, new_source_enabled):
                    st.success(f"已添加: {new_source_name}")
                    st.rerun()
                else:
                    st.error("添加失败，可能名称已存在")
            else:
                st.error("请填写名称和URL")

# ========== 关键词设置 ==========
elif page == "🔑 关键词设置":
    st.title("🔑 关键词设置")
    st.markdown("设置用于筛选学术信息的关键词")

    keywords_data = config_manager.get_keywords()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("英文关键词")
        en_keywords = keywords_data.get('keywords', [])
        en_text = st.text_area(
            "每行一个关键词",
            value="\n".join(en_keywords),
            height=300,
            key="en_keywords"
        )

    with col2:
        st.subheader("中文关键词")
        cn_keywords = keywords_data.get('keywords_cn', [])
        cn_text = st.text_area(
            "每行一个关键词",
            value="\n".join(cn_keywords),
            height=300,
            key="cn_keywords"
        )

    if st.button("💾 保存关键词", type="primary"):
        new_en = [k.strip() for k in en_text.split("\n") if k.strip()]
        new_cn = [k.strip() for k in cn_text.split("\n") if k.strip()]

        if config_manager.update_keywords(new_en, new_cn):
            st.success("关键词已保存")
            st.rerun()
        else:
            st.error("保存失败")

    st.divider()

    # 关键词建议
    st.subheader("💡 关键词建议")
    suggested = [
        ("学术研究", ["artificial intelligence", "machine learning", "deep learning", "neural network"]),
        ("公共管理", ["public governance", "digital governance", "e-government", "smart city"]),
        ("数据科学", ["big data", "data mining", "data governance", "algorithm"])
    ]

    for category, words in suggested:
        st.markdown(f"**{category}**: {', '.join(words)}")

# ========== 提醒管理 ==========
elif page == "⏰ 提醒管理":
    st.title("⏰ 提醒管理")
    st.markdown("设置日程提醒时间")

    reminders = config_manager.get_reminders()

    # 显示现有提醒
    if reminders:
        st.subheader("当前提醒")
        for i, reminder in enumerate(reminders):
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 2, 3, 1])

                with col1:
                    new_time = st.text_input(
                        "时间",
                        reminder['time'],
                        key=f"remind_time_{i}",
                        label_visibility="collapsed"
                    )

                with col2:
                    new_title = st.text_input(
                        "标题",
                        reminder['title'],
                        key=f"remind_title_{i}",
                        label_visibility="collapsed"
                    )

                with col3:
                    new_desc = st.text_input(
                        "描述",
                        reminder['description'],
                        key=f"remind_desc_{i}",
                        label_visibility="collapsed"
                    )

                with col4:
                    if st.button("🗑️", key=f"delete_remind_{i}"):
                        if config_manager.delete_reminder(i):
                            st.rerun()

                # 保存按钮
                if st.button("💾 保存", key=f"save_remind_{i}"):
                    config_manager.update_reminder(i, time=new_time, title=new_title, description=new_desc)
                    st.success("已保存")
                    st.rerun()

                st.divider()

    # 添加新提醒
    st.subheader("➕ 添加提醒")
    with st.form("add_reminder_form"):
        col1, col2 = st.columns(2)

        with col1:
            remind_time = st.text_input("时间 (HH:MM)", value="09:00")
            remind_title = st.text_input("标题", placeholder="例如: 早晨学习")

        with col2:
            remind_desc = st.text_area("描述", placeholder="提醒内容描述")

        submitted = st.form_submit_button("添加提醒", use_container_width=True)
        if submitted:
            if remind_time and remind_title:
                if config_manager.add_reminder(remind_time, remind_title, remind_desc):
                    st.success("已添加提醒")
                    st.rerun()
            else:
                st.error("请填写时间和标题")

# ========== 邮箱配置 ==========
elif page == "📧 邮箱配置":
    st.title("📧 邮箱配置")
    st.markdown("配置邮件发送功能，用于发送学术简报")

    email_config = config_manager.get_email_config()

    with st.form("email_form"):
        enabled = st.checkbox("启用邮件发送", value=email_config.get('enabled', False))

        col1, col2 = st.columns(2)

        with col1:
            smtp_server = st.text_input(
                "SMTP服务器",
                value=email_config.get('smtp_server', 'smtp.qq.com')
            )
            sender_email = st.text_input(
                "发件人邮箱",
                value=email_config.get('sender_email', '')
            )
            sender_password = st.text_input(
                "授权密码",
                value=email_config.get('sender_password', ''),
                type="password"
            )

        with col2:
            smtp_port = st.number_input(
                "SMTP端口",
                value=email_config.get('smtp_port', 587)
            )
            receiver_email = st.text_input(
                "收件人邮箱",
                value=email_config.get('receiver_email', '')
            )
            subject_prefix = st.text_input(
                "邮件主题前缀",
                value=email_config.get('subject_prefix', '[学术简报]')
            )

        submitted = st.form_submit_button("保存配置", type="primary", use_container_width=True)
        if submitted:
            new_config = {
                'enabled': enabled,
                'smtp_server': smtp_server,
                'smtp_port': int(smtp_port),
                'sender_email': sender_email,
                'sender_password': sender_password,
                'receiver_email': receiver_email,
                'subject_prefix': subject_prefix
            }
            if config_manager.update_email_config(new_config):
                st.success("邮箱配置已保存")
            else:
                st.error("保存失败")

    st.divider()

    # 常用邮箱配置
    st.subheader("📋 常用邮箱SMTP配置")
    smtp_info = [
        ("QQ邮箱", "smtp.qq.com", "587/465", "需要开启SMTP服务并获取授权码"),
        ("163邮箱", "smtp.163.com", "25/465", "需要开启SMTP服务"),
        ("Gmail", "smtp.gmail.com", "587", "需要应用专用密码"),
        ("Outlook", "smtp-mail.outlook.com", "587", "直接使用账号密码")
    ]

    for name, server, port, note in smtp_info:
        st.markdown(f"**{name}**: `{server}` 端口: {port} - _{note}_")

# ========== 课程表 ==========
elif page == "📅 课程表":
    st.title("📅 课程表管理")
    st.markdown("管理每周课程安排")

    schedule = config_manager.get_schedule()
    week_schedule = schedule.get('week_schedule', {})

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_names = {
        "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
        "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
    }

    # 选择要编辑的日期
    selected_day = st.selectbox(
        "选择日期",
        days,
        format_func=lambda x: day_names.get(x, x)
    )

    # 显示该天的课程
    st.subheader(f"{day_names[selected_day]}课程")
    courses = week_schedule.get(selected_day, [])

    if courses:
        for i, course in enumerate(courses):
            with st.expander(f"📚 {course.get('name', '未命名')} - {course.get('time', '')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**时间**: {course.get('time', '')}")
                    st.markdown(f"**地点**: {course.get('location', '')}")
                with col2:
                    st.markdown(f"**教师**: {course.get('teacher', '')}")
                    st.markdown(f"**备注**: {course.get('note', '')}")

                if st.button("删除此课程", key=f"del_course_{selected_day}_{i}"):
                    if config_manager.delete_course(selected_day, i):
                        st.rerun()
    else:
        st.info("该天暂无课程安排")

    st.divider()

    # 添加新课程
    st.subheader("➕ 添加课程")
    with st.form("add_course_form"):
        col1, col2 = st.columns(2)

        with col1:
            course_name = st.text_input("课程名称")
            course_time = st.text_input("时间", placeholder="例如: 10:00-12:25")
            course_location = st.text_input("地点")

        with col2:
            course_teacher = st.text_input("教师")
            course_note = st.text_input("备注")

        submitted = st.form_submit_button("添加课程", use_container_width=True)
        if submitted:
            if course_name and course_time:
                if config_manager.add_course(selected_day, course_name, course_time,
                                             course_location or "", course_teacher or "",
                                             course_note or ""):
                    st.success("课程已添加")
                    st.rerun()
            else:
                st.error("请填写课程名称和时间")

    # 显示学期信息
    st.divider()
    semester = schedule.get('semester', '')
    if semester:
        st.caption(f"学期: {semester}")

# ========== 高级设置 ==========
elif page == "⚙️ 高级设置":
    st.title("⚙️ 高级设置")

    # 翻译设置
    st.subheader("🌐 翻译设置")
    trans_config = config_manager.get_translation_config()

    col1, col2 = st.columns(2)
    with col1:
        trans_enabled = st.checkbox("启用翻译", value=trans_config.get('enabled', False))
    with col2:
        target_lang = st.selectbox("目标语言", ["en", "zh"], index=0 if trans_config.get('target_lang') == 'en' else 1)

    if st.button("保存翻译设置"):
        if config_manager.update_translation_config(trans_enabled, target_lang):
            st.success("已保存")

    st.divider()

    # 输出设置
    st.subheader("📄 输出设置")
    output_settings = config_manager.get_output_settings()

    col1, col2 = st.columns(2)
    with col1:
        output_format = st.selectbox(
            "输出格式",
            ["markdown", "html"],
            index=0 if output_settings.get('output_format') == 'markdown' else 1
        )
    with col2:
        max_items = st.number_input(
            "每个来源最大条目数",
            min_value=1,
            max_value=20,
            value=output_settings.get('max_items_per_source', 5)
        )

    if st.button("保存输出设置"):
        if config_manager.update_output_settings(output_format, max_items):
            st.success("已保存")

    st.divider()

    # 复习任务（来自schedule.json）
    st.subheader("📖 复习任务设置")
    schedule = config_manager.get_schedule()
    review_tasks = schedule.get('review_tasks', {})

    if review_tasks:
        for task_name, task_info in review_tasks.items():
            st.markdown(f"- **{task_name}**: {task_info.get('duration', '')} (优先级: {task_info.get('priority', '')})")
    else:
        st.info("暂无复习任务设置")

# ========== 导入导出 ==========
elif page == "💾 导入导出":
    st.title("💾 配置导入导出")
    st.markdown("备份或恢复您的配置")

    # 导出
    st.subheader("📤 导出配置")
    st.markdown("将当前所有配置导出为JSON文件")

    if st.button("生成导出文件", type="primary"):
        export_data = config_manager.export_all_config()
        st.download_button(
            label="下载配置文件",
            data=json.dumps(export_data, ensure_ascii=False, indent=2),
            file_name=f"daily_automation_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    st.divider()

    # 导入
    st.subheader("📥 导入配置")
    st.markdown("从JSON文件恢复配置")

    uploaded_file = st.file_uploader("选择配置文件", type=["json"])

    if uploaded_file is not None:
        try:
            import_data = json.load(uploaded_file)
            st.json(import_data)

            if st.button("确认导入", type="primary"):
                if config_manager.import_all_config(import_data):
                    st.success("配置已导入")
                    st.rerun()
                else:
                    st.error("导入失败")
        except Exception as e:
            st.error(f"文件解析失败: {e}")

    st.divider()

    # 重置
    st.subheader("🔄 重置配置")
    st.warning("此操作将清除所有自定义配置，恢复为默认值")

    if st.button("重置为默认配置", type="secondary"):
        config_manager.reset_to_default()
        st.success("已重置为默认配置")
        st.rerun()
