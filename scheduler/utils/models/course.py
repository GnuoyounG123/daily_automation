from dataclasses import dataclass
from typing import List, Dict
import csv
import re
from pathlib import Path


@dataclass
class Course:
    """课程数据模型"""
    name: str
    time: str
    location: str
    teacher: str
    exam_time: str
    
    @classmethod
    def from_zdbk_dict(cls, data: Dict) -> 'Course':
        """
        从教务系统原始数据创建Course对象（数据在kcb字段中）
        
        Args:
            data: 教务系统返回的课程数据字典
        
        Returns:
            Course对象
        """
        kcb = data.get('kcb', '')
        parts = kcb.split('<br>')
        
        name = parts[0].strip() if len(parts) > 0 else ''
        time_info = parts[1] if len(parts) > 1 else ''
        teacher = parts[2].strip() if len(parts) > 2 else ''
        location_exam = parts[3] if len(parts) > 3 else ''
        
        location = ''
        exam_time = ''
        
        if location_exam:
            exam_match = re.search(r'\d{4}年\d{2}月\d{2}日\([^)]+\)', location_exam)
            if exam_match:
                exam_time = exam_match.group(0)
                location = location_exam.replace(exam_match.group(0), '').replace('zwf', '').strip()
            else:
                location = location_exam.replace('zwf', '').strip()
        
        week_day_map = {'1': '周一', '2': '周二', '3': '周三', 
                       '4': '周四', '5': '周五', '6': '周六', '7': '周日'}
        xqj = str(data.get('xqj', ''))
        week_day = week_day_map.get(xqj, '')
        
        time_str = f"{week_day} {time_info}" if week_day else time_info
        
        return cls(
            name=name,
            time=time_str,
            location=location,
            teacher=teacher,
            exam_time=exam_time if exam_time else '未安排'
        )
    
    def to_dict(self) -> Dict:
        """转换为字典（用于缓存）"""
        return {
            'name': self.name,
            'time': self.time,
            'location': self.location,
            'teacher': self.teacher,
            'exam_time': self.exam_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Course':
        """从字典创建Course对象（用于缓存恢复）"""
        return cls(
            name=data.get('name', ''),
            time=data.get('time', ''),
            location=data.get('location', ''),
            teacher=data.get('teacher', ''),
            exam_time=data.get('exam_time', '未安排')
        )
    
    def to_csv_dict(self) -> Dict:
        """转换为CSV格式的字典"""
        return {
            '课程名称': self.name,
            '上课时间': self.time,
            '上课地点': self.location,
            '教师信息': self.teacher,
            '考试时间': self.exam_time
        }


class CourseExporter:
    """课程导出器"""
    
    @staticmethod
    def to_csv(courses: List[Course], filepath: Path) -> None:
        """
        导出课程到CSV文件
        
        Args:
            courses: 课程列表
            filepath: 输出文件路径
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            if not courses:
                f.write('课程名称,上课时间,上课地点,教师信息,考试时间\n')
                return
            
            writer = csv.DictWriter(f, fieldnames=['课程名称', '上课时间', '上课地点', '教师信息', '考试时间'])
            writer.writeheader()
            
            for course in courses:
                writer.writerow(course.to_csv_dict())
    
    @staticmethod
    def to_dict_list(courses: List[Course]) -> List[Dict]:
        """
        转换课程列表为字典列表
        
        Args:
            courses: 课程列表
        
        Returns:
            字典列表
        """
        return [course.to_csv_dict() for course in courses]