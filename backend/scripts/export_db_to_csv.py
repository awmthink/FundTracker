import sqlite3
import csv
import os
from datetime import datetime

def export_db_to_csv():
    # 创建导出目录
    export_dir = 'db_exports'
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    
    # 生成时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 连接数据库
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    try:
        # 导出 funds 表
        cursor.execute('SELECT * FROM funds')
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        funds_file = os.path.join(export_dir, f'funds_{timestamp}.csv')
        with open(funds_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)  # 写入表头
            writer.writerows(rows)    # 写入数据
        
        print(f"Funds table exported to: {funds_file}")
        
        # 导出 fund_transactions 表
        cursor.execute('SELECT * FROM fund_transactions')
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        transactions_file = os.path.join(export_dir, f'fund_transactions_{timestamp}.csv')
        with open(transactions_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)  # 写入表头
            writer.writerows(rows)    # 写入数据
            
        print(f"Fund transactions table exported to: {transactions_file}")
        
        return {
            'funds_file': funds_file,
            'transactions_file': transactions_file
        }
        
    except Exception as e:
        print(f"Error exporting database: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    try:
        export_db_to_csv()
        print("Database export completed successfully!")
    except Exception as e:
        print(f"Export failed: {str(e)}")
