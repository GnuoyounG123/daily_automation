from icalendar import Calendar, Event, Alarm
from datetime import datetime, timedelta
from typing import List, Dict
import re


class ICalExporter:
    @staticmethod
    def parse_exam_time(exam_str: str) -> tuple:
        """
        解析考试时间字符串
        
        示例: "2025年06月15日(09:00-11:00)"
        返回: (datetime对象, 持续分钟数)
        """
        match = re.match(r'(\d{4})年(\d{2})月(\d{2})日\((\d{2}):(\d{2})-(\d{2}):(\d{2})\)', exam_str)
        if not match:
            return None, None
        
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        start_hour = int(match.group(4))
        start_min = int(match.group(5))
        end_hour = int(match.group(6))
        end_min = int(match.group(7))
        
        start_dt = datetime(year, month, day, start_hour, start_min)
        end_dt = datetime(year, month, day, end_hour, end_min)
        duration = int((end_dt - start_dt).total_seconds() / 60)
        
        return start_dt, duration
    
    @staticmethod
    def export_exams(exams: List[Dict], output_path: str, semester_name: str = "2025春夏学期"):
        """
        导出考试信息到iCal文件
        
        Args:
            exams: 考试列表，每项包含name, location, teacher, exam_time
            output_path: 输出文件路径
            semester_name: 学期名称
        """
        cal = Calendar()
        cal.add('prodid', '-//浙江大学课表//zju-schedule//CN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('x-wr-calname', f'浙江大学 {semester_name} 考试安排')
        
        for exam in exams:
            start_dt, duration = ICalExporter.parse_exam_time(exam['exam_time'])
            
            if not start_dt:
                continue
            
            event = Event()
            event.add('summary', f"【考试】{exam['name']}")
            event.add('dtstart', start_dt)
            event.add('dtend', start_dt + timedelta(minutes=duration))
            event.add('dtstamp', datetime.now())
            event.add('location', exam.get('location', '待定'))
            event.add('description', f"任课教师: {exam.get('teacher', '未知')}")
            event.add('uid', f"{exam['name']}-{start_dt.strftime('%Y%m%d%H%M')}@zju-schedule")
            event.add('categories', 'EXAM')
            event.add('priority', 1)
            
            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('description', f"明天考试: {exam['name']}")
            alarm.add('trigger', timedelta(hours=-24))
            event.add_component(alarm)
            
            cal.add_component(event)
        
        with open(output_path, 'wb') as f:
            f.write(cal.to_ical())
        
        return len(exams)