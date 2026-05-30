from typing import List, Dict, Optional
from models.course import Course
import re


class TimetableGrid:
    TIMESLOTS = [
        ("第1节", "08:00-08:45"),
        ("第2节", "08:55-09:40"),
        ("第3节", "09:50-10:35"),
        ("第4节", "10:45-11:30"),
        ("第5节", "11:40-12:25"),
        ("第6节", "13:15-14:00"),
        ("第7节", "14:10-14:55"),
        ("第8节", "15:05-15:50"),
        ("第9节", "16:00-16:45"),
        ("第10节", "16:55-17:40"),
        ("第11节", "18:30-19:15"),
        ("第12节", "19:25-20:10"),
        ("第13节", "20:20-21:05"),
    ]
    
    WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    def __init__(self):
        self.grid: Dict[str, Dict[int, List[Dict]]] = {}
        for day in self.WEEKDAYS:
            self.grid[day] = {i: [] for i in range(1, 14)}
    
    def parse_time_slot(self, time_str: str) -> tuple:
        """
        解析时间字符串，返回(星期几, 节次列表)
        
        示例:
        - "周一 1-2节" -> ('周一', [1, 2])
        - "周三 3-4节" -> ('周三', [3, 4])
        - "周五 6,7,8节" -> ('周五', [6, 7, 8])
        """
        day_match = re.match(r'(周[一二三四五六日])', time_str)
        if not day_match:
            return None, []
        
        day = day_match.group(1)
        
        sections = []
        section_str = time_str.replace(day, '').strip()
        
        range_match = re.search(r'(\d+)-(\d+)节', section_str)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            sections = list(range(start, end + 1))
        else:
            single_matches = re.findall(r'(\d+)节', section_str)
            sections = [int(s) for s in single_matches]
        
        return day, sections
    
    def add_course(self, course: Course):
        """添加课程到课表网格"""
        day, sections = self.parse_time_slot(course.time)
        
        if not day or not sections:
            return
        
        course_info = {
            'name': course.name,
            'location': course.location,
            'teacher': course.teacher,
            'exam_time': course.exam_time
        }
        
        for section in sections:
            if 1 <= section <= 13:
                self.grid[day][section].append(course_info)
    
    def load_courses(self, courses: List[Course]):
        """加载课程列表"""
        for course in courses:
            self.add_course(course)
    
    def get_cell_content(self, day: str, section: int) -> str:
        """获取单元格内容"""
        courses = self.grid[day][section]
        if not courses:
            return ''
        
        if len(courses) == 1:
            c = courses[0]
            return f"{c['name']}\n{c['location']}"
        else:
            names = [c['name'] for c in courses]
            return '\n'.join(names)
    
    def get_courses_for_section(self, day: str, section: int) -> List[Dict]:
        """获取某节次的所有课程"""
        return self.grid[day][section]
    
    def get_all_exam_info(self) -> List[Dict]:
        """获取所有考试信息"""
        exams = []
        seen = set()
        
        for day in self.WEEKDAYS:
            for section in range(1, 14):
                for course in self.grid[day][section]:
                    if course['exam_time'] and course['exam_time'] != '未安排':
                        key = (course['name'], course['exam_time'])
                        if key not in seen:
                            exams.append(course)
                            seen.add(key)
        
        return exams
    
    def get_section_time(self, section: int) -> str:
        """获取节次对应的时间"""
        if 1 <= section <= 13:
            return self.TIMESLOTS[section - 1][1]
        return ''