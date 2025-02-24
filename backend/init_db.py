import sqlite3
import os

def init_db():
    # 检查数据库文件是否存在，如果存在则删除
    if os.path.exists('finance.db'):
        os.remove('finance.db')
    
    # 创建新的数据库连接
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    # 读取 schema.sql 文件
    with open('database/schema.sql', 'r') as f:
        schema = f.read()
    
    # 执行 SQL 语句
    cursor.executescript(schema)
    
    # 提交更改并关闭连接
    conn.commit()
    conn.close()
    
    print("数据库初始化完成！")

if __name__ == '__main__':
    init_db() 