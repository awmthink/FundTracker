import sqlite3
from flask import jsonify
from datetime import datetime
import requests
import re
import json

class FundService:
    def __init__(self):
        self.db_name = 'finance.db'

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def add_transaction(self, data):
        # 数据验证
        required_fields = ['fund_code', 'fund_name', 'transaction_type', 
                          'amount', 'nav', 'fee', 'transaction_date']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必要字段: {field}'
                })
        
        # 验证数值字段
        try:
            amount = float(data['amount'])
            nav = float(data['nav'])
            fee = float(data['fee'])
            if amount <= 0 or nav <= 0:
                return jsonify({
                    'status': 'error',
                    'message': '金额和净值必须大于0'
                })
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '金额、净值或手续费格式不正确'
            })
        
        # 验证交易类型
        if data['transaction_type'] not in ['buy', 'sell']:
            return jsonify({
                'status': 'error',
                'message': '交易类型必须是 buy 或 sell'
            })

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查基金是否存在，不存在则添加
            cursor.execute('''
                INSERT OR IGNORE INTO funds (fund_code, fund_name, current_nav)
                VALUES (?, ?, ?)
            ''', (data['fund_code'], data['fund_name'], data['nav']))
            
            # 获取基金ID
            cursor.execute('SELECT fund_id FROM funds WHERE fund_code = ?', 
                          (data['fund_code'],))
            fund_id = cursor.fetchone()[0]
            
            # 计算手续费
            if data['transaction_type'] == 'sell':
                fee = self.calculate_sell_fee(
                    data['fund_code'],
                    float(data['amount']),
                    data['transaction_date']
                )
            else:
                # 买入手续费计算保持不变
                fund_settings = self.get_fund_fees(data['fund_code'])
                if not fund_settings:
                    return jsonify({
                        'status': 'error',
                        'message': '未找到基金费率设置'
                    })
                fee = float(data['amount']) * fund_settings['buy_fee']
            
            # 计算份额
            shares = float(data['amount']) / float(data['nav'])
            
            # 添加交易记录
            cursor.execute('''
                INSERT INTO fund_transactions 
                (fund_id, transaction_type, amount, nav, fee, transaction_date, shares)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fund_id, data['transaction_type'], amount, nav,
                  fee, data['transaction_date'], shares))
            
            conn.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            conn.rollback()
            return jsonify({
                'status': 'error',
                'message': f'数据库错误: {str(e)}'
            })
        finally:
            conn.close()

    def get_holdings(self):
        """获取基金持仓信息"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 查询持仓信息，包括成本、份额、当前净值等
            cursor.execute('''
                SELECT 
                    f.fund_code,
                    f.fund_name,
                    f.current_nav,
                    f.last_update_time,
                    SUM(CASE 
                        WHEN t.transaction_type = 'buy' THEN t.shares 
                        WHEN t.transaction_type = 'sell' THEN -t.shares 
                        ELSE 0 
                    END) as total_shares,
                    SUM(CASE 
                        WHEN t.transaction_type = 'buy' THEN t.amount 
                        WHEN t.transaction_type = 'sell' THEN -t.amount 
                        ELSE 0 
                    END) as total_cost
                FROM funds f
                LEFT JOIN fund_transactions t ON f.fund_id = t.fund_id
                GROUP BY f.fund_id, f.fund_code, f.fund_name
                HAVING total_shares > 0
            ''')
            
            holdings = []
            for row in cursor.fetchall():
                total_shares = float(row['total_shares'] or 0)
                total_cost = float(row['total_cost'] or 0)
                current_nav = float(row['current_nav'] or 0)
                current_value = total_shares * current_nav
                
                # 计算收益
                profit = current_value - total_cost
                profit_rate = (profit / total_cost * 100) if total_cost > 0 else 0
                
                holdings.append({
                    'fund_code': row['fund_code'],
                    'fund_name': row['fund_name'],
                    'total_shares': total_shares,
                    'total_cost': total_cost,
                    'current_nav': current_nav,
                    'current_value': current_value,
                    'profit': profit,
                    'profit_rate': profit_rate,
                    'last_update_time': row['last_update_time']
                })
            
            return holdings
            
        except Exception as e:
            print(f"Error getting holdings: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise
        finally:
            if 'conn' in locals():
                conn.close()

    def update_nav(self, data):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE funds 
                SET current_nav = ?,
                    last_update_time = ?
                WHERE fund_code = ?
            ''', (data['current_nav'], datetime.now(), data['fund_code']))
            
            conn.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': str(e)})
        finally:
            conn.close()

    def get_fund_settings(self):
        """获取所有基金设置"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT fund_code, fund_name, buy_fee, sell_fee_short, 
                       sell_fee_long, created_at, updated_at 
                FROM fund_settings
                ORDER BY created_at DESC
            ''')
            settings = cursor.fetchall()
            return [{
                'fund_code': row['fund_code'],
                'fund_name': row['fund_name'],
                'buy_fee': float(row['buy_fee']),
                'sell_fee_short': float(row['sell_fee_short']),
                'sell_fee_long': float(row['sell_fee_long']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            } for row in settings]
        finally:
            conn.close()

    def save_fund_settings(self, fund_data):
        """保存基金费率设置"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO fund_settings (
                    fund_code, fund_name, buy_fee, 
                    sell_fee_lt7, sell_fee_lt365, sell_fee_gt365,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                fund_data['fund_code'],
                fund_data['fund_name'],
                fund_data['buy_fee'],
                fund_data['sell_fee_lt7'],
                fund_data['sell_fee_lt365'],
                fund_data['sell_fee_gt365']
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"保存基金设置失败: {str(e)}")
            return False
        finally:
            conn.close()

    def delete_fund_settings(self, fund_code):
        """删除基金设置"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM fund_settings WHERE fund_code = ?', 
                         (fund_code,))
            conn.commit()
        finally:
            conn.close()

    def get_fund_fees(self, fund_code):
        """获取指定基金的费率设置"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT buy_fee, sell_fee_lt7, sell_fee_lt365, sell_fee_gt365 
                FROM fund_settings 
                WHERE fund_code = ?
            ''', (fund_code,))
            row = cursor.fetchone()
            if row:
                return {
                    'buy_fee': float(row['buy_fee']),
                    'sell_fee_lt7': float(row['sell_fee_lt7']),
                    'sell_fee_lt365': float(row['sell_fee_lt365']),
                    'sell_fee_gt365': float(row['sell_fee_gt365'])
                }
            return None
        finally:
            conn.close()

    def calculate_sell_fee(self, fund_code, sell_amount, transaction_date):
        """
        计算赎回费用
        :param fund_code: 基金代码
        :param sell_amount: 赎回金额
        :param transaction_date: 赎回日期
        :return: 手续费金额
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取基金的所有买入记录，按照购买日期排序
            cursor.execute('''
                SELECT t.transaction_date, t.shares, t.nav
                FROM fund_transactions t
                JOIN funds f ON t.fund_id = f.fund_id
                WHERE f.fund_code = ? AND t.transaction_type = 'buy'
                ORDER BY t.transaction_date ASC
            ''', (fund_code,))
            
            buy_records = cursor.fetchall()
            
            # 获取基金费率设置
            cursor.execute('''
                SELECT sell_fee_lt7, sell_fee_lt365, sell_fee_gt365
                FROM fund_settings
                WHERE fund_code = ?
            ''', (fund_code,))
            
            fee_settings = cursor.fetchone()
            if not fee_settings:
                raise ValueError("未找到基金费率设置")
                
            sell_fee_lt7, sell_fee_lt365, sell_fee_gt365 = fee_settings
            
            # 计算每笔买入记录到赎回日期的持有天数
            total_fee = 0
            remaining_amount = sell_amount
            sell_date = datetime.strptime(transaction_date, '%Y-%m-%d')
            
            for buy_record in buy_records:
                buy_date = datetime.strptime(buy_record[0], '%Y-%m-%d')
                shares = buy_record[1]
                nav = buy_record[2]
                
                holding_days = (sell_date - buy_date).days
                current_amount = shares * nav
                
                if remaining_amount <= 0:
                    break
                    
                amount_to_sell = min(remaining_amount, current_amount)
                
                # 根据持有天数确定费率
                if holding_days < 7:
                    fee_rate = sell_fee_lt7
                elif holding_days < 365:
                    fee_rate = sell_fee_lt365
                else:
                    fee_rate = sell_fee_gt365
                    
                fee = amount_to_sell * fee_rate
                total_fee += fee
                remaining_amount -= amount_to_sell
                
            return total_fee
            
        finally:
            conn.close()

    def fetch_fund_info(self, fund_code):
        """从天天基金网获取基金信息"""
        try:
            print(f"Fetching fund info for code: {fund_code}")
            
            # 使用天天基金的另一个API接口
            url = f'http://fund.eastmoney.com/pingzhongdata/{fund_code}.js'
            print(f"Requesting URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'http://fund.eastmoney.com/',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                
                # 解析基金名称
                name_match = re.search(r'fS_name = "([^"]+)"', content)
                code_match = re.search(r'fS_code = "([^"]+)"', content)
                
                if name_match and code_match:
                    fund_name = name_match.group(1)
                    fund_code = code_match.group(1)
                    
                    result = {
                        'code': fund_code,
                        'name': fund_name
                    }
                    print(f"Parsed result: {result}")
                    return result
                else:
                    print("Could not find fund name or code in response")
            
            return None
            
        except Exception as e:
            import traceback
            print(f"Error in fetch_fund_info: {str(e)}")
            print(traceback.format_exc())
            return None

    def fetch_current_nav(self, fund_code):
        """获取基金当前净值"""
        try:
            print(f"Fetching current NAV for fund: {fund_code}")
            
            # 使用天天基金的API
            url = f'http://fundgz.1234567.com.cn/js/{fund_code}.js'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'http://fund.eastmoney.com/'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
            
            if response.status_code == 200:
                # 解析返回的数据，格式为：jsonpgz({"fundcode":"001186","name":"富国文体健康股票","jzrq":"2024-01-19","dwjz":"1.5397","gsz":"1.5558","gszzl":"1.05"});
                content = response.text
                if 'jsonpgz(' in content and ');' in content:
                    json_str = content.replace('jsonpgz(', '').replace(');', '')
                    print(f"Extracted JSON: {json_str}")
                    
                    fund_data = json.loads(json_str)
                    
                    # 获取净值信息
                    nav = float(fund_data.get('gsz', 0)) or float(fund_data.get('dwjz', 0))
                    update_time = fund_data.get('jzrq')
                    
                    print(f"Parsed NAV: {nav}, Update time: {update_time}")
                    
                    # 更新数据库
                    conn = self.get_db_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE funds 
                            SET current_nav = ?, last_update_time = ? 
                            WHERE fund_code = ?
                        ''', (nav, update_time, fund_code))
                        conn.commit()
                    finally:
                        conn.close()
                    
                    return {
                        'nav': nav,
                        'update_time': update_time
                    }
            
            return None
            
        except Exception as e:
            import traceback
            print(f"Error fetching current NAV: {str(e)}")
            print(traceback.format_exc())
            return None

    def update_all_navs(self):
        """更新所有基金的最新净值"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 获取所有基金代码
            cursor.execute('SELECT fund_code FROM funds')
            funds = cursor.fetchall()
            
            updated_count = 0
            for fund in funds:
                fund_code = fund['fund_code']
                result = self.fetch_current_nav(fund_code)
                if result:
                    updated_count += 1
            
            return {
                'total': len(funds),
                'updated': updated_count
            }
            
        except Exception as e:
            print(f"Error updating all NAVs: {str(e)}")
            raise
        finally:
            if 'conn' in locals():
                conn.close() 