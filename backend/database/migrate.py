import sqlite3
import os

def migrate_database():
    """为现有数据库添加 target_investment 字段"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'finance.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(funds)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'target_investment' not in column_names:
            print("添加 target_investment 字段...")
            cursor.execute("ALTER TABLE funds ADD COLUMN target_investment REAL DEFAULT 0")
            conn.commit()
            print("迁移完成！")
        else:
            print("target_investment 字段已存在，无需迁移")
    except Exception as e:
        print(f"迁移失败: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database() 