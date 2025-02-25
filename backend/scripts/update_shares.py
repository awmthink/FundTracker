import sqlite3
from pathlib import Path

def get_db_connection():
    """获取数据库连接"""
    db_path = Path(__file__).parent.parent / 'finance.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_fund_fees(cursor, fund_code):
    """获取基金费率设置"""
    cursor.execute('''
        SELECT buy_fee, sell_fee_lt7, sell_fee_lt365, sell_fee_gt365
        FROM fund_settings
        WHERE fund_code = ?
    ''', (fund_code,))
    result = cursor.fetchone()
    if result:
        return {
            'buy_fee': float(result['buy_fee']),
            'sell_fee_lt7': float(result['sell_fee_lt7']),
            'sell_fee_lt365': float(result['sell_fee_lt365']),
            'sell_fee_gt365': float(result['sell_fee_gt365'])
        }
    return None

def update_transaction_shares():
    """更新交易记录中的份额"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取所有交易记录
        cursor.execute('''
            SELECT ft.*, f.fund_code
            FROM fund_transactions ft
            JOIN funds f ON ft.fund_id = f.fund_id
            ORDER BY transaction_date
        ''')
        transactions = cursor.fetchall()
        
        updated_count = 0
        for transaction in transactions:
            amount = float(transaction['amount'])
            nav = float(transaction['nav'])
            
            if transaction['transaction_type'] == 'buy':
                # 获取基金费率
                fund_settings = get_fund_fees(cursor, transaction['fund_code'])
                if not fund_settings:
                    print(f"警告: 未找到基金 {transaction['fund_code']} 的费率设置")
                    continue
                
                # 重新计算买入份额
                fee = amount * fund_settings['buy_fee']
                shares = (amount - fee) / nav
                
                # 更新交易记录
                cursor.execute('''
                    UPDATE fund_transactions
                    SET shares = ?, fee = ?
                    WHERE transaction_id = ?
                ''', (shares, fee, transaction['transaction_id']))
                
                updated_count += 1
                print(f"更新交易记录 ID: {transaction['transaction_id']}, "
                      f"基金代码: {transaction['fund_code']}, "
                      f"原份额: {transaction['shares']}, "
                      f"新份额: {shares}")
        
        conn.commit()
        print(f"\n成功更新 {updated_count} 条交易记录")
        
    except Exception as e:
        conn.rollback()
        print(f"更新失败: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    confirm = input("此操作将更新所有买入交易的份额数据，是否继续？(y/n): ")
    if confirm.lower() == 'y':
        update_transaction_shares()
    else:
        print("操作已取消") 