# 计算器后端服务

## 项目介绍
这是前后端分离计算器项目的后端部分，基于 Python Flask 框架开发，提供计算API、计算历史存储与查询服务。

## 技术栈
- **后端框架**: Flask 2.3.3
- **数据库**: SQLite 3（轻量级文件数据库，无需单独安装）
- **跨域处理**: Flask-CORS

## 功能说明
1. **安全表达式计算** - 支持加减乘除、括号、正负号、小数，不使用eval()，通过中缀转后缀算法安全计算
2. **计算历史存储** - 自动将每次成功计算保存到数据库
3. **历史记录查询** - 提供接口获取所有计算历史
4. **历史记录删除** - 支持删除单条记录或清空全部

## 运行环境
- Python 3.8+

## 安装与启动

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动服务
```bash
python app.py
```

服务启动后默认运行在 `http://localhost:5000`

## API 接口说明

### 健康检查
- **GET** `/api/health`
- 返回服务状态

### 计算接口
- **POST** `/api/calculate`
- 请求体: `{ "expression": "1+2*3" }`
- 成功返回: `{ "success": true, "expression": "1+2*3", "result": 7 }`
- 失败返回: `{ "success": false, "message": "错误信息" }`

### 获取历史
- **GET** `/api/history`
- 返回所有计算历史记录

### 删除单条历史
- **DELETE** `/api/history/<id>`
- 根据ID删除指定记录

### 清空所有历史
- **DELETE** `/api/history`
- 清空所有计算记录

## 数据库设计
数据库表 `calculation_history`:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| expression | TEXT | 计算表达式 |
| result | TEXT | 计算结果 |
| created_at | TIMESTAMP | 计算时间 |

## 前后端连接
前端通过 HTTP 请求访问本服务的 API 接口，默认地址为 `http://localhost:5000/api`。
部署时请修改前端代码中的 `API_BASE` 变量为线上后端地址。
