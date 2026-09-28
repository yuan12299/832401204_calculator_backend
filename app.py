from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import re

app = Flask(__name__)
CORS(app)  # 允许跨域，方便前后端分离开发

DATABASE = 'calculator.db'

# ========== 数据库操作 ==========

def init_db():
    """初始化数据库，创建历史记录表"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calculation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expression TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_history(expression, result):
    """保存一条计算记录"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO calculation_history (expression, result) VALUES (?, ?)',
        (expression, str(result))
    )
    conn.commit()
    conn.close()

def get_all_history():
    """获取所有历史记录，按时间倒序"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM calculation_history ORDER BY created_at DESC')
    rows = cursor.fetchall()
    history = [dict(row) for row in rows]
    conn.close()
    return history

def delete_history_by_id(record_id):
    """删除指定ID的历史记录"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM calculation_history WHERE id = ?', (record_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def clear_all_history():
    """清空所有历史记录"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM calculation_history')
    conn.commit()
    conn.close()

# ========== 安全的表达式计算 ==========

def tokenize(expression):
    """把表达式字符串拆成一个个 token（数字、运算符、括号）"""
    # 处理负号：把开头的-或者运算符后面的-当成负号，用特殊标记_代替
    tokens = []
    i = 0
    expr = expression.replace(' ', '')  # 去掉所有空格
    
    while i < len(expr):
        char = expr[i]
        
        # 数字（包括小数）
        if char.isdigit() or char == '.':
            j = i
            while j < len(expr) and (expr[j].isdigit() or expr[j] == '.'):
                j += 1
            tokens.append(('number', float(expr[i:j])))
            i = j
        # 运算符和括号
        elif char in '+-*/()':
            # 判断是不是负号：开头的-，或者前面是运算符/左括号
            if char == '-' and (i == 0 or expr[i-1] in '+-*/('):
                tokens.append(('op', 'u-'))  # 一元负号
            elif char == '+' and (i == 0 or expr[i-1] in '+-*/('):
                tokens.append(('op', 'u+'))  # 一元正号
            else:
                tokens.append(('op', char))
            i += 1
        else:
            raise ValueError(f"不允许的字符: {char}")
    
    return tokens

def precedence(op):
    """运算符优先级"""
    if op in ('+', '-'):
        return 1
    if op in ('*', '/'):
        return 2
    if op in ('u+', 'u-'):
        return 3
    return 0

def infix_to_postfix(tokens):
    """中缀表达式转后缀表达式（逆波兰表达式）"""
    output = []
    stack = []
    
    for token_type, token_value in tokens:
        if token_type == 'number':
            output.append(token_value)
        elif token_value == '(':
            stack.append(token_value)
        elif token_value == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            if not stack:
                raise ValueError("括号不匹配")
            stack.pop()  # 弹出左括号
        else:  # 运算符
            while (stack and stack[-1] != '(' and 
                   precedence(stack[-1]) >= precedence(token_value)):
                output.append(stack.pop())
            stack.append(token_value)
    
    while stack:
        if stack[-1] == '(':
            raise ValueError("括号不匹配")
        output.append(stack.pop())
    
    return output

def eval_postfix(postfix):
    """计算后缀表达式的值"""
    stack = []
    
    for token in postfix:
        if isinstance(token, float):
            stack.append(token)
        else:
            if token in ('u+', 'u-'):  # 一元运算符
                if not stack:
                    raise ValueError("表达式错误")
                val = stack.pop()
                if token == 'u-':
                    stack.append(-val)
                else:
                    stack.append(val)
            else:  # 二元运算符
                if len(stack) < 2:
                    raise ValueError("表达式错误")
                b = stack.pop()
                a = stack.pop()
                if token == '+':
                    stack.append(a + b)
                elif token == '-':
                    stack.append(a - b)
                elif token == '*':
                    stack.append(a * b)
                elif token == '/':
                    if b == 0:
                        raise ZeroDivisionError("除数不能为零")
                    stack.append(a / b)
    
    if len(stack) != 1:
        raise ValueError("表达式不完整")
    
    result = stack[0]
    # 如果是整数就转成整数显示，不然保留小数
    if result == int(result):
        return int(result)
    return round(result, 10)  # 避免浮点数精度问题

def calculate(expression):
    """计算数学表达式，安全实现，不用eval"""
    # 先验证输入只包含允许的字符
    if not re.match(r'^[\d\.\+\-\*/\(\)\s]+$', expression):
        raise ValueError("表达式包含不允许的字符")
    
    tokens = tokenize(expression)
    postfix = infix_to_postfix(tokens)
    result = eval_postfix(postfix)
    return result

# ========== API 接口 ==========

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    """计算接口：接收表达式，返回结果"""
    data = request.get_json()
    
    if not data or 'expression' not in data:
        return jsonify({'success': False, 'message': '缺少expression参数'}), 400
    
    expression = data['expression'].strip()
    
    if not expression:
        return jsonify({'success': False, 'message': '表达式不能为空'}), 400
    
    try:
        result = calculate(expression)
        # 保存到历史
        save_history(expression, result)
        return jsonify({
            'success': True,
            'expression': expression,
            'result': result
        })
    except ZeroDivisionError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500

@app.route('/api/history', methods=['GET'])
def api_get_history():
    """获取所有计算历史"""
    try:
        history = get_all_history()
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'message': '获取历史失败'}), 500

@app.route('/api/history/<int:record_id>', methods=['DELETE'])
def api_delete_history(record_id):
    """删除指定ID的历史记录"""
    try:
        deleted = delete_history_by_id(record_id)
        if deleted:
            return jsonify({'success': True, 'message': '删除成功'})
        else:
            return jsonify({'success': False, 'message': '记录不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': '删除失败'}), 500

@app.route('/api/history', methods=['DELETE'])
def api_clear_history():
    """清空所有历史记录"""
    try:
        clear_all_history()
        return jsonify({'success': True, 'message': '已清空所有历史'})
    except Exception as e:
        return jsonify({'success': False, 'message': '清空失败'}), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'message': 'Calculator API is running'})

# ========== 启动 ==========

if __name__ == '__main__':
    init_db()
    print("计算器后端服务已启动！")
    print("API地址: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
