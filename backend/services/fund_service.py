import sqlite3
from flask import jsonify
from datetime import datetime, timedelta
import requests
import re
import json

class FundService:
    def __init__(self):
        self.db_name = 'finance.db'
        self.fund_api_url = "http://fundgz.1234567.com.cn/js"

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def add_transaction(self, data):
        """添加交易记录"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 数据验证
            required_fields = ['fund_code', 'fund_name', 'transaction_type', 
                             'amount', 'nav', 'transaction_date']
            for field in required_fields:
                if field not in data:
                    return {
                        'status': 'error',
                        'message': f'缺少必需字段: {field}'
                    }
            
            # 如果是卖出交易，验证是否有足够的份额
            if data['transaction_type'] == 'sell':
                cursor.execute('''
                    SELECT COALESCE(
                        SUM(CASE 
                            WHEN transaction_type = 'buy' THEN shares 
                            WHEN transaction_type = 'sell' THEN -shares 
                            ELSE 0 
                        END), 0) as available_shares
                    FROM fund_transactions ft
                    JOIN funds f ON ft.fund_id = f.fund_id
                    WHERE f.fund_code = ?
                    AND transaction_date <= ?
                ''', (data['fund_code'], data['transaction_date']))
                
                available_shares = cursor.fetchone()[0]
                sell_shares = float(data['amount']) / float(data['nav'])
                
                if sell_shares > available_shares:
                    return {
                        'status': 'error',
                        'message': f'可用份额不足。当前可用: {available_shares:.2f}, 尝试卖出: {sell_shares:.2f}'
                    }
            
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
                fund_settings = self.get_fund_fees(data['fund_code'])
                if not fund_settings:
                    return {
                        'status': 'error',
                        'message': '未找到基金费率设置'
                    }
                fee = float(data['amount']) * fund_settings['buy_fee']
            
            # 计算份额
            shares = float(data['amount']) / float(data['nav'])
            
            # 添加交易记录
            cursor.execute('''
                INSERT INTO fund_transactions 
                (fund_id, transaction_type, amount, nav, fee, transaction_date, shares)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fund_id, data['transaction_type'], data['amount'], data['nav'],
                  fee, data['transaction_date'], shares))
            
            # 更新基金当前净值
            cursor.execute('''
                UPDATE funds 
                SET current_nav = ?, last_update_time = CURRENT_TIMESTAMP
                WHERE fund_id = ?
            ''', (data['nav'], fund_id))
            
            conn.commit()
            return {
                'status': 'success',
                'message': '交易添加成功'
            }
        except Exception as e:
            conn.rollback()
            print(f"添加交易失败: {str(e)}")  # 添加错误日志
            return {
                'status': 'error',
                'message': f'添加交易失败: {str(e)}'
            }
        finally:
            conn.close()

    def get_historical_nav(self, fund_code, date):
        """从天天基金获取历史净值"""
        try:
            # 使用天天基金的历史净值接口
            url = f"http://fund.eastmoney.com/f10/F10DataApi.aspx"
            params = {
                'type': 'lsjz',  # 历史净值
                'code': fund_code,
                'page': 1,
                'per': 1,  # 只获取一条记录
                'sdate': date,
                'edate': date
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                print(f"获取基金{fund_code}净值失败: HTTP {response.status_code}")
                return None
            
            # 返回的是HTML格式的数据，需要解析
            content = response.text
            
            # 使用正则表达式提取数据
            import re
            pattern = r'<td>(\d{4}-\d{2}-\d{2})</td><td.*?>(.*?)</td>'
            matches = re.findall(pattern, content)
            
            if matches:
                for date_str, nav_str in matches:
                    if date_str == date:  # 确保日期匹配
                        try:
                            return float(nav_str)
                        except ValueError:
                            print(f"净值转换失败: {nav_str}")
                            return None
            
            # 如果没有找到对应日期的数据，尝试获取最近的净值
            url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
            params = {
                'rt': datetime.now().timestamp()
            }
            
            response = requests.get(url, params=params, headers=headers)
            if response.status_code == 200:
                content = response.text
                # 返回格式类似：jsonpgz({"fundcode":"000001","name":"xxx","jzrq":"2023-11-23","dwjz":"1.0100",...})
                match = re.search(r'"dwjz":"([\d\.]+)"', content)
                if match:
                    return float(match.group(1))
            
            return None
            
        except Exception as e:
            print(f"获取基金{fund_code}历史净值失败: {str(e)}")
            return None

    def get_holdings(self):
        """获取基金持仓信息"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取前一个工作日的日期
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 如果是周一，获取上周五的数据
            if datetime.now().weekday() == 0:  # 0 表示周一
                yesterday = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            # 如果是周日，获取周五的数据
            elif datetime.now().weekday() == 6:  # 6 表示周日
                yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
            
            print(f"获取 {yesterday} 的净值数据")  # 添加日志
            
            cursor.execute('''
                WITH fund_summary AS (
                    SELECT 
                        f.fund_id,
                        f.fund_code,
                        f.fund_name,
                        f.current_nav,
                        SUM(CASE 
                            WHEN t.transaction_type = 'buy' THEN t.shares 
                            WHEN t.transaction_type = 'sell' THEN -t.shares 
                            ELSE 0 
                        END) as total_shares,
                        SUM(CASE 
                            WHEN t.transaction_type = 'buy' THEN t.amount + t.fee
                            WHEN t.transaction_type = 'sell' THEN -(t.amount + t.fee)
                            ELSE 0 
                        END) as total_cost
                    FROM funds f
                    LEFT JOIN fund_transactions t ON f.fund_id = t.fund_id
                    GROUP BY f.fund_id, f.fund_code, f.fund_name, f.current_nav
                    HAVING total_shares > 0
                )
                SELECT 
                    fund_code,
                    fund_name,
                    current_nav,
                    total_shares,
                    total_cost as cost_amount
                FROM fund_summary
                ORDER BY total_cost DESC
            ''')
            
            holdings = cursor.fetchall()
            
            # 转换为字典列表并获取最新净值
            result = []
            for row in holdings:
                # 获取昨日净值
                yesterday_nav = self.get_historical_nav(row[0], yesterday)
                nav = yesterday_nav if yesterday_nav is not None else row[2]
                
                print(f"基金 {row[0]} 的净值: {nav}")  # 添加日志
                
                total_shares = float(row[3]) if row[3] is not None else 0
                cost_amount = float(row[4]) if row[4] is not None else 0
                market_value = total_shares * float(nav)
                profit_loss = market_value - cost_amount
                profit_rate = profit_loss / cost_amount if cost_amount > 0 else 0
                
                holding = {
                    'fund_code': row[0],
                    'fund_name': row[1],
                    'current_nav': float(nav),
                    'total_shares': total_shares,
                    'cost_amount': cost_amount,
                    'market_value': market_value,
                    'profit_loss': profit_loss,
                    'profit_rate': profit_rate
                }
                result.append(holding)
            
            return result
            
        except Exception as e:
            print(f"获取持仓信息失败: {str(e)}")
            raise e
        finally:
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

    def calculate_sell_fee(self, fund_code, amount, transaction_date):
        """计算赎回费用"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取基金费率设置
            cursor.execute('''
                SELECT sell_fee_lt7, sell_fee_lt365, sell_fee_gt365
                FROM fund_settings
                WHERE fund_code = ?
            ''', (fund_code,))
            
            fee_settings = cursor.fetchone()
            if not fee_settings:
                raise Exception('未找到基金费率设置')
            
            # 获取最早的买入日期
            cursor.execute('''
                SELECT MIN(transaction_date)
                FROM fund_transactions ft
                JOIN funds f ON ft.fund_id = f.fund_id
                WHERE f.fund_code = ?
                AND ft.transaction_type = 'buy'
            ''', (fund_code,))
            
            earliest_buy_date = cursor.fetchone()[0]
            if not earliest_buy_date:
                raise Exception('未找到买入记录')
            
            # 计算持有天数
            earliest_buy_date = datetime.strptime(earliest_buy_date, '%Y-%m-%d')
            current_date = datetime.strptime(transaction_date, '%Y-%m-%d')
            hold_days = (current_date - earliest_buy_date).days
            
            # 根据持有期确定费率
            if hold_days < 7:
                fee_rate = fee_settings[0]  # sell_fee_lt7
            elif hold_days < 365:
                fee_rate = fee_settings[1]  # sell_fee_lt365
            else:
                fee_rate = fee_settings[2]  # sell_fee_gt365
            
            return amount * fee_rate
            
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

    def get_transactions(self, filters=None):
        """获取基金交易记录"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            query = '''
                SELECT 
                    t.transaction_id,
                    f.fund_code,
                    f.fund_name,
                    t.transaction_type,
                    t.amount,
                    t.nav,
                    t.fee,
                    t.shares,
                    t.transaction_date
                FROM fund_transactions t
                JOIN funds f ON t.fund_id = f.fund_id
                WHERE 1=1
            '''
            params = []
            
            if filters:
                if filters.get('fund_code'):
                    query += ' AND f.fund_code LIKE ?'
                    params.append(f"%{filters['fund_code']}%")
                if filters.get('fund_name'):
                    query += ' AND f.fund_name LIKE ?'
                    params.append(f"%{filters['fund_name']}%")
                if filters.get('start_date'):
                    query += ' AND t.transaction_date >= ?'
                    params.append(filters['start_date'])
                if filters.get('end_date'):
                    query += ' AND t.transaction_date <= ?'
                    params.append(filters['end_date'])
                if filters.get('transaction_type'):
                    query += ' AND t.transaction_type = ?'
                    params.append(filters['transaction_type'])
            
            query += ' ORDER BY t.transaction_date DESC'
            
            cursor.execute(query, params)
            transactions = cursor.fetchall()
            
            return [{
                'transaction_id': row['transaction_id'],
                'fund_code': row['fund_code'],
                'fund_name': row['fund_name'],
                'transaction_type': row['transaction_type'],
                'amount': float(row['amount']),
                'nav': float(row['nav']),
                'fee': float(row['fee']),
                'shares': float(row['shares']),
                'transaction_date': row['transaction_date']
            } for row in transactions]
            
        finally:
            conn.close()

    def delete_transaction(self, transaction_id):
        """删除交易记录"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM fund_transactions WHERE transaction_id = ?', 
                          (transaction_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_transaction(self, transaction_id, data):
        """更新交易记录"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 验证必需字段
            required_fields = ['fund_code', 'fund_name', 'transaction_type', 
                             'amount', 'nav', 'transaction_date']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f'缺少必需字段: {field}')

            # 确保数值字段为浮点数
            amount = float(data['amount'])
            nav = float(data['nav'])
            
            # 验证交易记录是否存在
            cursor.execute('SELECT * FROM fund_transactions WHERE transaction_id = ?', 
                          (transaction_id,))
            if not cursor.fetchone():
                raise ValueError('交易记录不存在')

            # 获取基金ID
            cursor.execute('SELECT fund_id FROM funds WHERE fund_code = ?', 
                          (data['fund_code'],))
            fund_result = cursor.fetchone()
            if not fund_result:
                raise ValueError('基金不存在')
            
            fund_id = fund_result[0]
            
            # 计算手续费
            if data['transaction_type'] == 'sell':
                fee = self.calculate_sell_fee(
                    data['fund_code'],
                    amount,
                    data['transaction_date']
                )
            else:
                fund_settings = self.get_fund_fees(data['fund_code'])
                if not fund_settings:
                    raise ValueError('未找到基金费率设置')
                fee = amount * fund_settings['buy_fee']
            
            # 计算份额
            shares = amount / nav
            
            # 更新交易记录
            cursor.execute('''
                UPDATE fund_transactions 
                SET fund_id = ?, 
                    transaction_type = ?, 
                    amount = ?, 
                    nav = ?, 
                    fee = ?, 
                    transaction_date = ?, 
                    shares = ?
                WHERE transaction_id = ?
            ''', (fund_id, data['transaction_type'], amount, nav, fee,
                  data['transaction_date'], shares, transaction_id))
            
            if cursor.rowcount == 0:
                raise ValueError('更新失败，未找到对应的交易记录')
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"更新交易记录失败: {str(e)}")  # 添加日志输出
            raise e
        finally:
            conn.close() 