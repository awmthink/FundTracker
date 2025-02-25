# backend/scripts/merge_tables.py
import sqlite3

def merge_fund_tables():
    """合并 funds 和 fund_settings 表"""
    conn = sqlite3.connect('finance.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        # 备份现有数据
        cursor.execute('CREATE TABLE IF NOT EXISTS funds_backup AS SELECT * FROM funds')
        cursor.execute('CREATE TABLE IF NOT EXISTS fund_settings_backup AS SELECT * FROM fund_settings')
        
        # 创建新表，保持原有的 fund_id
        cursor.execute('''
            CREATE TABLE funds_new (
                fund_id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_code TEXT NOT NULL UNIQUE,
                fund_name TEXT NOT NULL,
                current_nav REAL DEFAULT 0,
                last_update_time DATETIME,
                buy_fee REAL DEFAULT 0,
                sell_fee_lt7 REAL DEFAULT 0,
                sell_fee_lt365 REAL DEFAULT 0,
                sell_fee_gt365 REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 合并数据时保留原有的 fund_id
        cursor.execute('''
            INSERT INTO funds_new (
                fund_id, fund_code, fund_name, current_nav, last_update_time,
                buy_fee, sell_fee_lt7, sell_fee_lt365, sell_fee_gt365
            )
            SELECT 
                f.fund_id,
                f.fund_code, 
                f.fund_name, 
                f.current_nav, 
                f.last_update_time,
                COALESCE(fs.buy_fee, 0), 
                COALESCE(fs.sell_fee_lt7, 0),
                COALESCE(fs.sell_fee_lt365, 0),
                COALESCE(fs.sell_fee_gt365, 0)
            FROM funds f
            LEFT JOIN fund_settings fs ON f.fund_code = fs.fund_code
        ''')
        
        # 验证数据迁移
        cursor.execute('SELECT COUNT(*) FROM funds')
        old_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM funds_new')
        new_count = cursor.fetchone()[0]
        
        if old_count != new_count:
            raise Exception(f"数据迁移验证失败: 原表数量 {old_count}, 新表数量 {new_count}")
        
        # 验证 fund_transactions 表中的外键关系
        cursor.execute('''
            SELECT COUNT(DISTINCT ft.fund_id) as transaction_fund_count,
                   COUNT(DISTINCT f.fund_id) as new_fund_count
            FROM fund_transactions ft
            LEFT JOIN funds_new f ON ft.fund_id = f.fund_id
        ''')
        counts = cursor.fetchone()
        if counts[0] != counts[1]:
            raise Exception("交易表中的 fund_id 与新基金表不匹配")
        
        # 删除旧表并重命名新表
        cursor.execute('DROP TABLE IF EXISTS funds')
        cursor.execute('DROP TABLE IF EXISTS fund_settings')
        cursor.execute('ALTER TABLE funds_new RENAME TO funds')
        
        # 添加外键约束
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_fund_transactions_fund_id 
            ON fund_transactions(fund_id)
        ''')
        
        conn.commit()
        print("表合并完成")
        
    except Exception as e:
        conn.rollback()
        print(f"合并表失败: {str(e)}")
        # 恢复备份
        try:
            cursor.execute('DROP TABLE IF EXISTS funds')
            cursor.execute('ALTER TABLE funds_backup RENAME TO funds')
            cursor.execute('DROP TABLE IF EXISTS fund_settings')
            cursor.execute('ALTER TABLE fund_settings_backup RENAME TO fund_settings')
            conn.commit()
            print("备份恢复成功")
        except Exception as restore_error:
            print(f"备份恢复失败: {str(restore_error)}")
    finally:
        conn.close()


if __name__ == "__main__":
    merge_fund_tables()