# 浙江大学教务系统抓取服务

基于 Flask 的教务系统课表抓取服务，模块化设计，支持测试。

## 项目结构

```
schedule/zju/
├── app.py                 # Flask主应用
├── config.py              # 配置文件
├── credentials.json       # 登录凭证
├── requirements.txt       # Python依赖
├── services/              # 服务层
│   ├── __init__.py
│   ├── sso.py            # SSO登录服务
│   └── zdbk.py           # 教务系统服务
├── models/                # 数据模型层
│   ├── __init__.py
│   └── course.py         # 课程模型和导出
├── utils/                 # 工具层
│   ├── __init__.py
│   └── crypto.py         # RSA加密工具
├── tests/                 # 测试层
│   ├── __init__.py
│   └── test_course.py    # 单元测试
└── output/                # 输出目录
    └── timetable_*.csv   # 课表CSV文件
```

## 快速开始

### 1. 安装依赖

```bash
cd schedule/zju
pip install -r requirements.txt
```

### 2. 配置凭证

编辑 `credentials.json` 文件：

```json
{
  "username": "你的学号",
  "password": "你的密码"
}
```

### 3. 运行服务

```bash
python app.py
```

服务将在 `http://localhost:5000` 启动。

### 4. 测试接口

#### 健康检查

```bash
curl http://localhost:5000/health
```

#### 获取当前学期课表

```bash
curl http://localhost:5000/api/timetable/current
```

#### 获取指定学期课表

```bash
curl http://localhost:5000/api/timetable/2025/2|夏
```

#### 获取验证码图片

```bash
curl http://localhost:5000/api/captcha --output captcha.jpg
```

## API 接口

### GET /health

健康检查接口

**响应示例：**
```json
{
  "status": "ok"
}
```

### GET /api/timetable/current

获取当前学期课表（2025-2026年春夏学期）

**响应示例：**
```json
{
  "success": true,
  "year": 2025,
  "semester": "2|夏",
  "count": 10,
  "courses": [
    {
      "课程名称": "高等数学",
      "上课时间": "周一 1-2节 1-16周",
      "上课地点": "教学楼A101",
      "教师信息": "张三",
      "考试时间": "2025年6月15日 09:00-11:00"
    }
  ],
  "csv_file": "/path/to/timetable_2025_2_夏.csv"
}
```

### GET /api/timetable/<year>/<semester>

获取指定学年学期的课表

**路径参数：**
- `year`: 学年（如2025表示2025-2026学年）
- `semester`: 学期（格式如"1|秋", "1|冬", "2|春", "2|夏"）

## 运行测试

```bash
cd schedule/zju
python tests/test_course.py
```

## 学期格式说明

浙江大学学年学期格式：
- `1|秋`: 第一学期秋季
- `1|冬`: 第一学期冬季
- `2|春`: 第二学期春季
- `2|夏`: 第二学期夏季

当前学期（2025-2026年春夏学期）：`year=2025, semester="2|夏"`

## CSV 输出格式

课表CSV包含以下列：
- 课程名称
- 上课时间
- 上课地点
- 教师信息
- 考试时间

## 注意事项

1. 首次登录可能需要输入验证码（接口会返回 `need_captcha: true`）
2. 学号和密码请妥善保管，不要提交到版本控制系统
3. 如遇验证码，可通过 `/api/captcha` 接口获取验证码图片

## 原型机特性

- 模块化设计：服务层、模型层、工具层分离
- 可测试：提供单元测试样例
- 配置化：通过配置文件管理参数
- 错误处理：完善的异常处理机制
- RESTful API：标准的HTTP接口设计