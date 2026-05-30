import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.course import Course, CourseExporter


def test_course_from_dict():
    """测试从字典创建Course对象"""
    data = {
        'kcmc': '高等数学',
        'xqj': '1',
        'jc': '1-2',
        'zcd': '1-16周',
        'cdmc': '教学楼A101',
        'xm': '张三',
        'ksmc': '2025年6月15日 09:00-11:00'
    }
    
    course = Course.from_zdbk_dict(data)
    
    assert course.name == '高等数学'
    assert '周一' in course.time
    assert '1-2节' in course.time
    assert course.location == '教学楼A101'
    assert course.teacher == '张三'
    assert course.exam_time == '2025年6月15日 09:00-11:00'
    print("Course对象创建测试通过")


def test_course_to_dict():
    """测试Course对象转字典"""
    course = Course(
        name='线性代数',
        time='周二 3-4节 1-16周',
        location='教学楼B202',
        teacher='李四',
        exam_time='2025年6月16日 14:00-16:00'
    )
    
    result = course.to_dict()
    
    assert result['课程名称'] == '线性代数'
    assert result['上课时间'] == '周二 3-4节 1-16周'
    assert result['上课地点'] == '教学楼B202'
    assert result['教师信息'] == '李四'
    assert result['考试时间'] == '2025年6月16日 14:00-16:00'
    print("Course对象转字典测试通过")


def test_exporter_to_dict_list():
    """测试导出器转字典列表"""
    courses = [
        Course(
            name='课程A',
            time='周一 1-2节',
            location='教室A',
            teacher='教师A',
            exam_time='考试A'
        ),
        Course(
            name='课程B',
            time='周二 3-4节',
            location='教室B',
            teacher='教师B',
            exam_time='考试B'
        )
    ]
    
    result = CourseExporter.to_dict_list(courses)
    
    assert len(result) == 2
    assert result[0]['课程名称'] == '课程A'
    assert result[1]['课程名称'] == '课程B'
    print("导出器转字典列表测试通过")


if __name__ == '__main__':
    test_course_from_dict()
    test_course_to_dict()
    test_exporter_to_dict_list()
    print("\n所有测试通过！")