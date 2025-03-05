import sqlite3
import csv
import os
from datetime import datetime

def import_csv_to_db(funds_file=None, transactions_file=None):
    """
    从CSV文件导入数据到数据库
    :param funds_file: funds表的CSV文件路径
    :param transactions_file: fund_transactions表的CSV文件路径
    :return: 导入结果统计
    """
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()
    
    stats = {
        'funds': {'processed': 0, 'success': 0, 'error': 0},
        'transactions': {'processed': 0, 'success': 0, 'error': 0}
    }
    
    try:
        # 导入funds表数据
        if funds_file and os.path.exists(funds_file):
            with open(funds_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stats['funds']['processed'] += 1
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO funds (
                                fund_code, fund_name, current_nav, last_update_time,
                                buy_fee, fund_type, target_investment, investment_strategy,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row['fund_code'],
                            row['fund_name'],
                            float(row['current_nav']) if row['current_nav'] else 0,
                            row['last_update_time'],
                            float(row['buy_fee']) if row['buy_fee'] else 0,
                            row.get('fund_type', ''),
                            float(row.get('target_investment', 0)) if row.get('target_investment') else 0,
                            row.get('investment_strategy', ''),
                            row.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            row.get('updated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                        ))
                        stats['funds']['success'] += 1
                    except Exception as e:
                        print(f"Error importing fund {row.get('fund_code')}: {str(e)}")
                        stats['funds']['error'] += 1

        # 导入fund_transactions表数据
        if transactions_file and os.path.exists(transactions_file):
            with open(transactions_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stats['transactions']['processed'] += 1
                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO fund_transactions (
                                transaction_id, fund_code, transaction_type,
                                amount, nav, fee, transaction_date, shares
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            int(row['transaction_id']) if row.get('transaction_id') else None,
                            row['fund_code'],
                            row['transaction_type'],
                            float(row['amount']),
                            float(row['nav']),
                            float(row['fee']),
                            row['transaction_date'],
                            float(row['shares'])
                        ))
                        stats['transactions']['success'] += 1
                    except Exception as e:
                        print(f"Error importing transaction {row.get('transaction_id')}: {str(e)}")
                        stats['transactions']['error'] += 1

        conn.commit()
        return stats

    except Exception as e:
        print(f"Database import error: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def find_latest_exports():
    """
    在db_exports目录中查找最新的导出文件
    :return: (funds_file, transactions_file) 元组
    """
    export_dir = 'db_exports'
    if not os.path.exists(export_dir):
        return None, None

    funds_files = [f for f in os.listdir(export_dir) if f.startswith('funds_')]
    trans_files = [f for f in os.listdir(export_dir) if f.startswith('fund_transactions_')]
    
    latest_funds = max(funds_files) if funds_files else None
    latest_trans = max(trans_files) if trans_files else None
    
    return (
        os.path.join(export_dir, latest_funds) if latest_funds else None,
        os.path.join(export_dir, latest_trans) if latest_trans else None
    )

if __name__ == '__main__':
    try:
        # 查找最新的导出文件
        funds_file, transactions_file = find_latest_exports()
        
        if not funds_file and not transactions_file:
            print("No export files found in db_exports directory!")
            exit(1)
            
        print(f"Found export files:\nFunds: {funds_file}\nTransactions: {transactions_file}")
        
        # 执行导入
        stats = import_csv_to_db(funds_file, transactions_file)
        
        # 打印导入结果
        print("\nImport completed!")
        print("\nFunds table statistics:")
        print(f"Processed: {stats['funds']['processed']}")
        print(f"Success: {stats['funds']['success']}")
        print(f"Errors: {stats['funds']['error']}")
        
        print("\nTransactions table statistics:")
        print(f"Processed: {stats['transactions']['processed']}")
        print(f"Success: {stats['transactions']['success']}")
        print(f"Errors: {stats['transactions']['error']}")
        
    except Exception as e:
        print(f"Import failed: {str(e)}")
