# 浙江大学教务管理系统接口文档

> 本文档整理自 Celechron 项目源码分析  
> 涵盖本科生教务网(zdbk)、研究生教务系统(yjsy)、学在浙大(courses)等子系统

---

## 目录

- [一、统一身份认证(SSO)](#一统一身份认证sso)
- [二、本科生教务网(zdbk)](#二本科生教务网zdbk)
- [三、研究生教务系统(yjsy)](#三研究生教务系统yjsy)
- [四、学在浙大(courses)](#四学在浙大courses)
- [五、校园卡服务(elife)](#五校园卡服务elife)
- [六、通用规范与注意事项](#六通用规范与注意事项)
---
## 一、统一身份认证(SSO)
### 1.1 登录流程概述
所有教务子系统都通过浙大统一身份认证(`zjuam.zju.edu.cn`)进行登录，采用 **RSA加密传输密码**。
### 1.2 接口详情
#### 1.2.1 获取登录页（获取execution参数）
```http
GET https://zjuam.zju.edu.cn/cas/login
```
**响应处理：**
- 从HTML中提取 `name="execution" value="..."` 参数
- 保存响应中的Cookie
#### 1.2.2 获取RSA公钥
```http
GET https://zjuam.zju.edu.cn/cas/v2/getPubKey
```
**响应示例：**
```json
{
  "modulus": "a3b2c1d4e5f6...",  // 十六进制模数
  "exponent": "10001"             // 十六进制指数(通常为65537)
}
```
#### 1.2.3 提交登录
```http
POST https://zjuam.zju.edu.cn/cas/login
Content-Type: application/x-www-form-urlencoded; charset=utf-8
username={学号}&password={加密密码}&execution={execution}&_eventId=submit&rememberMe=true
```
**密码加密算法（Dart实现）：**
```dart
我来为你提取教务系统的核心接口文档。首先检查仓库状态并创建目录。

2 个工具调用
写入
C:\Users\22113\AppData\Roaming\CherryStudio\Data\Agents\xyxs713tw\find_repo.py
已完成
执行命令
查找daily_automation仓库位置
已完成

错误：AbortError（中止错误）：请求被中止
Request was aborted
详情

用户
04/13 23:50
提取教务管理系统（包括本科生、研究生）关于课程表、绩点等信息查询的核心接口，包含全部调用流程与注意事项，总结成为markdown，放置在前文提到的repo目录下daily_automation仓库下新建文件夹schedule/zju中

Tokens: 117

ACM-onedragon
04/13 23:40
2 个工具调用
读取文件
C:\Users\22113\AppData\Roaming\CherryStudio\Data\Agents\xyxs713tw\Celechron_http\ugrs_spider.dart
123 行, 5 KB
已完成
读取文件
C:\Users\22113\AppData\Roaming\CherryStudio\Data\Agents\xyxs713tw\Celechron_http\ugrs_spider.dart
153 行, 8 KB
已完成
读取文件
C:\Users\22113\AppData\Roaming\CherryStudio\Data\Agents\xyxs713tw\Celechron_http\zjuServices\zdbk.dart
30 行, 1 KB
已完成
本科生课表查询实现逻辑详解
本科生课表查询是 Celechron 最核心的功能之一，涉及顺序请求控制、验证码处理、数据解析等多个环节。

一、整体架构流程
Text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  UgrsSpider     │────▶│  Zdbk.getTimetable│────▶│  教务网API      │
│  (业务 orchestrator)│     │  (HTTP请求层)     │     │  (zdbk.zju.edu.cn)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
       │                         │                          │
       ▼                         ▼                          ▼
  按学年顺序抓取             验证码处理                      课表数据
  1|秋→1|冬→2|春→2|夏       最大3次重试                    JSON解析
二、UgrsSpider：业务编排层 (ugrs_spider.dart:234-272)
2.1 学期遍历策略
Dart
// 从入学年份到毕业年份遍历（本科默认7年学制）
while (yearEnroll <= yearNow && yearEnroll <= yearGraduate) {
  var yearStr = '$yearEnroll-${yearEnroll + 1}';
  // 每个学年抓取4个学段：秋、冬、春、夏
  for (var season in ['1|秋', '1|冬', '2|春', '2|夏']) {
    // ...
  }
}
2.2 关键：顺序请求控制
教务网对并发请求敏感，因此采用链式顺序请求：

Dart
Future<String?> handleTimetable(season) async {
  if (cancelTimetableFetch) {
    return Future.value("已取消");
  }
  var value = await _zdbk.getTimetable(_httpClient, yearStr, season);
  // ...
  // 如果触发验证码，取消后续请求
  if (value.item1.toString().contains("验证码")) {
    cancelTimetableFetch = true;
  }
}
// 链式执行：秋→冬→春→夏
for (var season in ['1|秋', '1|冬', '2|春', '2|夏']) {
  if (timetableFetches.isEmpty) {
    timetableFetches.add(handleTimetable(season));
  } else {
    // 关键：用 .then() 实现顺序执行
    timetableFetches.first = timetableFetches.first.then((value) async {
      var res = await handleTimetable(season);
      return value ?? res;  // 保留第一个错误
    });
  }
}
三、Zdbk.getTimetable：HTTP请求层 (zdbk.dart:179-252)
3.1 API端点与参数
Text
POST https://zdbk.zju.edu.cn/jwglxt/kbcx/xskbcx_cxXsKb.html
Content-Type: application/x-www-form-urlencoded; charset=utf-8
X-Requested-With: XMLHttpRequest
Cookie: JSESSIONID=xxx; route=xxx
请求体: xnm=2023&xqm=1|秋&captcha_value=
3.2 完整请求流程
Dart
for (var i = 0; i < 3; i++) {  // 最多3次尝试（验证码重试）
  request = await httpClient.postUrl(Uri.parse(
      "https://zdbk.zju.edu.cn/jwglxt/kbcx/xskbcx_cxXsKb.html"));
  
  // 1. 添加认证Cookie
  request.cookies.add(_jSessionId!);
  request.cookies.add(_route!);
  
  // 2. 设置AJAX请求头
  request.headers.contentType = ContentType(
      'application', 'x-www-form-urlencoded', charset: 'utf-8');
  request.headers.add('X-Requested-With', 'XMLHttpRequest');
  
  // 3. 发送参数（含验证码）
  request.add(utf8.encode(
      'xnm=$year&xqm=$semester&captcha_value=$_captcha'));
  
  response = await request.close();
  var responseText = await response.transform(utf8.decoder).join();
  
  // 4. 处理验证码错误
  if (responseText.contains("captcha_error")) {
    // 弹出验证码输入框
    var imageBytes = await getCaptcha(httpClient);
    var captcha = await ImageCodePortal.show(imageBytes: imageBytes, ...);
    _captcha = captcha.trim();
    continue;  // 重试
  }
  
  // 5. 解析数据
  var timetableJson = RegExp('(?<="kbList":)\\[(.*?)\\](?=,"xh")')
      .firstMatch(responseText)?.group(0);
}
四、验证码处理机制 (zdbk.dart:208-224, 427-447)
4.1 触发条件
当响应包含 "captcha_error" 时触发验证码流程。

4.2 验证码获取
Dart
Future<Uint8List> getCaptcha(HttpClient httpClient) async {
  request = await httpClient.getUrl(Uri.parse(
      "https://zdbk.zju.edu.cn/jwglxt/kaptcha?time=${DateTime.now().millisecondsSinceEpoch}"));
  request.cookies.add(_jSessionId!);
  request.cookies.add(_route!);
  response = await request.close();
  return await consolidateHttpClientResponseBytes(response);  // 返回图片字节
}
4.3 验证码弹窗交互
Dart
if (responseText.contains("captcha_error")) {
  if (GlobalStatus.isFirstScreenReq) {
    throw ExceptionWithMessage("需要验证码");  // 首次启动不弹窗
  }
  
  // 显示验证码输入界面
  var captcha = await ImageCodePortal.show(
      imageBytes: imageBytes,
      onRefresh: () async => await getCaptcha(httpClient)  // 刷新功能
  );
  
  if (captcha == null) {
    throw ExceptionWithMessage("验证码未填写");
  }
  _captcha = captcha.trim();
  continue;  // 使用新验证码重试
}
4.4 重试策略
最大重试次数：3次
首次启动：如果 GlobalStatus.isFirstScreenReq 为true，直接抛出错误（避免启动时弹窗）
取消后续请求：一旦触发验证码，设置 cancelTimetableFetch = true 取消同一学年的后续学段查询
五、数据解析与过滤 (zdbk.dart:226-237)
5.1 JSON提取
教务网返回的是HTML包裹的JSON，用正则提取：

Dart
// 返回格式示例：... "kbList":[{课程1},{课程2}],"xh":"学号" ...
var timetableJson = RegExp('(?<="kbList":)\\[(.*?)\\](?=,"xh")')
    .firstMatch(responseText)?.group(0);
5.2 数据过滤
Dart
var sessions = (jsonDecode(timetableJson) as List<dynamic>)
    .where((e) =>
        e['kcb'] != null &&           // 过滤无课程编号的
        (e['sfyjskc'] != "1"))        // 过滤研究生课程(sfyjskc=1)
    .map((e) => Session.fromZdbk(e)); // 转换为Session对象
5.3 缓存策略
Dart
_db?.setCachedWebPage('zdbk_Timetable$year$semester', timetableJson);
缓存键格式：zdbk_Timetable2023-20241|秋

六、Session模型转换
Session.fromZdbk(e) 将教务网原始数据转换为应用内部模型：

Dart
// 原始字段示例
{
  "kcb": "课程编号",
  "kcmc": "课程名称",
  "xqj": "1",        // 星期几(1-7)
  "jc": "1-2",       // 节次
  "zcd": "1-16周",   // 上课周
  "cdmc": "教室",    
  "xm": "教师姓名",
  "sfyjskc": "0"     // 是否研究生课(0=否,1=是)
}
七、错误处理与降级
错误类型	处理方式
网络超时	抛出 ExceptionWithMessage("请求超时")
验证码错误	重试3次，失败后抛出
解析失败	抛出 ExceptionWithMessage("无法解析")
网络错误	返回缓存数据
Dart
catch (e) {
  var exception = e is SocketException 
      ? ExceptionWithMessage("网络错误") 
      : e as Exception;
  // 返回缓存
  return Tuple(exception, 
      (jsonDecode(_db?.getCachedWebPage('zdbk_Timetable$year$semester') ?? '[]'))
          .map((e) => Session.fromZdbk(e)));
}
八、关键点总结
顺序请求：使用 .then() 链式调用确保4个学段顺序执行，避免并发触发风控
验证码防护：最大3次重试 + 用户交互输入 + 首次启动保护
数据过滤：双重过滤（无编号课程 + 研究生课程）
离线可用：完整的缓存机制，网络异常时返回缓存数据
超时控制：8秒请求超时，防止长时间挂起

