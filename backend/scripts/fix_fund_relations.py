import sqlite3

def fix_fund_relations():
    """修复基金关联关系"""
    conn = sqlite3.connect('finance.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        # 检查孤立的交易记录
        cursor.execute('''
            SELECT COUNT(*) as orphan_count
            FROM fund_transactions ft
            LEFT JOIN funds f ON ft.fund_id = f.fund_id
            WHERE f.fund_id IS NULL
        ''')
        orphan_count = cursor.fetchone()['orphan_count']
        
        if orphan_count > 0:
            print(f"发现 {orphan_count} 条孤立的交易记录")
            
            # 获取孤立的交易记录详情
            cursor.execute('''
                SELECT ft.*, f.fund_code
                FROM fund_transactions ft
                LEFT JOIN funds f ON ft.fund_id = f.fund_id
                WHERE f.fund_id IS NULL
            ''')
            orphan_transactions = cursor.fetchall()
            
            # 尝试根据其他信息修复关联
            for transaction in orphan_transactions:
                # 在这里可以添加具体的修复逻辑
                print(f"正在处理交易ID: {transaction['transaction_id']}")
                
                # 示例：如果有基金代码信息，尝试重新关联
                if transaction['fund_code']:
                    cursor.execute('''
                        UPDATE fund_transactions
                        SET fund_id = (
                            SELECT fund_id 
                            FROM funds 
                            WHERE fund_code = ?
                        )
                        WHERE transaction_id = ?
                    ''', (transaction['fund_code'], transaction['transaction_id']))
        
        # 验证修复结果
        cursor.execute('''
            SELECT 
                f.fund_code,
                COUNT(ft.transaction_id) as transaction_count
            FROM funds f
            LEFT JOIN fund_transactions ft ON f.fund_id = ft.fund_id
            GROUP BY f.fund_code
        ''')
        
        fund_stats = cursor.fetchall()
        print("\n基金交易统计:")
        for stat in fund_stats:
            print(f"基金代码: {stat['fund_code']}, 交易记录数: {stat['transaction_count']}")
        
        conn.commit()
        print("\n关联关系修复完成")
        
    except Exception as e:
        conn.rollback()
        print(f"修复失败: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    fix_fund_relations() 