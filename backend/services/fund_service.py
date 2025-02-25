import sqlite3
from flask import jsonify
from datetime import datetime, timedelta
import requests
import re
import json
from typing import Optional, Dict, Any

class FundService:
    def __init__(self):
        self.db_name = 'finance.db'
        self.base_urls = {
            'fund_info': 'http://fund.eastmoney.com/pingzhongdata/{}.js',
            'current_nav': 'http://fundgz.1234567.com.cn/js/{}.js',
            'historical_nav': 'http://fund.eastmoney.com/f10/F10DataApi.aspx'
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://fund.eastmoney.com/',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[str]:
        """统一的HTTP请求处理"""
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=5)
            if response.status_code == 200:
                return response.text
            print(f"Request failed with status code: {response.status_code}")
            return None
        except Exception as e:
            print(f"Request error: {str(e)}")
            return None

    def fetch_fund_info(self, fund_code: str) -> Optional[Dict[str, str]]:
        """获取基金基本信息"""
        url = self.base_urls['fund_info'].format(fund_code)
        content = self._make_request(url)
        
        if not content:
            return None
            
        name_match = re.search(r'fS_name = "([^"]+)"', content)
        code_match = re.search(r'fS_code = "([^"]+)"', content)
        
        if name_match and code_match:
            return {
                'code': code_match.group(1),
                'name': name_match.group(1)
            }
        return None

    def fetch_current_nav(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """获取基金当前净值"""
        url = self.base_urls['current_nav'].format(fund_code)
        content = self._make_request(url)
        
        if not content or 'jsonpgz(' not in content:
            return None
            
        try:
            json_str = content.replace('jsonpgz(', '').replace(');', '')
            fund_data = json.loads(json_str)
            
            nav = float(fund_data.get('gsz', 0)) or float(fund_data.get('dwjz', 0))
            update_time = fund_data.get('jzrq')
            
            if nav and update_time:
                self._update_fund_nav(fund_code, nav, update_time)
                return {'nav': nav, 'update_time': update_time}
        except Exception as e:
            print(f"Error parsing current NAV: {str(e)}")
        return None

    def get_historical_nav(self, fund_code: str, date: str) -> Optional[float]:
        """获取历史净值"""
        params = {
            'type': 'lsjz',
            'code': fund_code,
            'page': 1,
            'per': 1,
            'sdate': date,
            'edate': date
        }
        
        content = self._make_request(self.base_urls['historical_nav'], params)
        if not content:
            return None
            
        pattern = r'<td>(\d{4}-\d{2}-\d{2})</td><td.*?>(.*?)</td>'
        matches = re.findall(pattern, content)
        
        for date_str, nav_str in matches:
            if date_str == date:
                try:
                    return float(nav_str)
                except ValueError:
                    print(f"NAV conversion failed: {nav_str}")
                    
        # 如果没找到历史净值，尝试获取当前净值
        current_nav = self.fetch_current_nav(fund_code)
        return current_nav['nav'] if current_nav else None

    def _update_fund_nav(self, fund_code: str, nav: float, update_time: str) -> None:
        """更新基金净值到数据库"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE funds 
                SET current_nav = ?, last_update_time = ? 
                WHERE fund_code = ?
            ''', (nav, update_time, fund_code))
            conn.commit()
        except Exception as e:
            print(f"Error updating fund NAV: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

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

    def get_holdings(self):
        """获取基金持仓信息"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 获取前一个工作日的日期
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            if datetime.now().weekday() == 0:
                yesterday = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            elif datetime.now().weekday() == 6:
                yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')

            # 首先获取所有基金的交易记录，按日期排序
            cursor.execute('''
                SELECT 
                    f.fund_code,
                    f.fund_name,
                    f.current_nav,
                    t.transaction_type,
                    t.shares,
                    t.amount,
                    t.fee,
                    t.transaction_date,
                    t.nav as transaction_nav
                FROM funds f
                JOIN fund_transactions t ON f.fund_id = t.fund_id
                ORDER BY f.fund_code, t.transaction_date ASC
            ''')
            
            transactions = cursor.fetchall()
            
            # 按基金代码分组处理交易
            holdings = {}
            for row in transactions:
                fund_code = row[0]
                if fund_code not in holdings:
                    holdings[fund_code] = {
                        'fund_code': fund_code,
                        'fund_name': row[1],
                        'current_nav': row[2],
                        'total_shares': 0,
                        'total_cost': 0,
                        'realized_profit': 0,  # 已实现收益
                        'total_investment': 0  # 总投入
                    }
                
                fund = holdings[fund_code]
                transaction_type = row[3]
                shares = float(row[4])
                amount = float(row[5])
                fee = float(row[6])
                
                if transaction_type == 'buy':
                    # 买入时更新总份额和总成本
                    fund['total_shares'] += shares
                    fund['total_cost'] += (amount + fee)
                    fund['total_investment'] += (amount + fee)
                    
                elif transaction_type == 'sell':
                    # 卖出时，使用当前平均成本计算已实现收益
                    if fund['total_shares'] > 0:
                        avg_cost_per_share = fund['total_cost'] / fund['total_shares']
                        sell_cost = shares * avg_cost_per_share
                        sell_amount = amount - fee
                        
                        # 计算已实现收益
                        realized_profit = sell_amount - sell_cost
                        fund['realized_profit'] += realized_profit
                        
                        # 更新总份额和总成本
                        fund['total_shares'] -= shares
                        if fund['total_shares'] > 0:
                            fund['total_cost'] = avg_cost_per_share * fund['total_shares']
                        else:
                            fund['total_cost'] = 0

            # 计算最终持仓信息
            result = []
            for fund_code, fund in holdings.items():
                if fund['total_shares'] > 0:  # 只显示有持仓的基金
                    # 获取最新净值
                    current_nav = self.get_historical_nav(fund_code, yesterday) or fund['current_nav']
                    
                    # 计算当前持仓成本
                    current_cost = fund['total_cost']
                    
                    # 计算当前市值
                    market_value = fund['total_shares'] * float(current_nav)
                    
                    # 计算持有收益和收益率
                    holding_profit = market_value - current_cost
                    holding_profit_rate = holding_profit / current_cost if current_cost > 0 else 0
                    
                    # 计算累计收益（包括已实现和未实现）
                    total_profit = holding_profit + fund['realized_profit']
                    
                    result.append({
                        'fund_code': fund_code,
                        'fund_name': fund['fund_name'],
                        'current_nav': float(current_nav),
                        'total_shares': fund['total_shares'],
                        'cost_amount': current_cost,
                        'market_value': market_value,
                        'holding_profit': holding_profit,
                        'holding_profit_rate': holding_profit_rate,
                        'total_profit': total_profit,
                        'avg_cost_nav': current_cost / fund['total_shares'] if fund['total_shares'] > 0 else 0
                    })
            
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
        """计算赎回费用，按FIFO原则分别计算每笔买入对应的赎回费用"""
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
            
            # 获取基金ID
            cursor.execute('SELECT fund_id FROM funds WHERE fund_code = ?', (fund_code,))
            fund_id = cursor.fetchone()[0]
            
            # 获取所有未售出的买入记录（按日期排序）
            cursor.execute('''
                SELECT 
                    t.transaction_date,
                    t.shares as original_shares,
                    COALESCE(
                        (SELECT SUM(st.shares) 
                         FROM fund_transactions st 
                         WHERE st.transaction_type = 'sell'
                         AND st.reference_buy_id = t.transaction_id), 
                        0
                    ) as sold_shares,
                    t.nav as buy_nav
                FROM fund_transactions t
                WHERE t.fund_id = ?
                AND t.transaction_type = 'buy'
                ORDER BY t.transaction_date ASC
            ''', (fund_id,))
            
            buy_records = cursor.fetchall()
            
            # 计算需要卖出的份额
            shares_to_sell = amount / float(data['nav'])
            total_fee = 0
            remaining_to_sell = shares_to_sell
            
            sell_date = datetime.strptime(transaction_date, '%Y-%m-%d')
            
            for record in buy_records:
                buy_date = datetime.strptime(record['transaction_date'], '%Y-%m-%d')
                available_shares = record['original_shares'] - record['sold_shares']
                
                if available_shares <= 0:
                    continue
                    
                # 计算这笔买入记录可以卖出的份额
                shares_from_this_buy = min(remaining_to_sell, available_shares)
                if shares_from_this_buy <= 0:
                    break
                    
                # 计算持有天数
                hold_days = (sell_date - buy_date).days
                
                # 确定费率
                if hold_days < 7:
                    fee_rate = fee_settings['sell_fee_lt7']
                elif hold_days < 365:
                    fee_rate = fee_settings['sell_fee_lt365']
                else:
                    fee_rate = fee_settings['sell_fee_gt365']
                
                # 计算这部分份额对应的金额和费用
                amount_for_this_portion = shares_from_this_buy * float(data['nav'])
                fee_for_this_portion = amount_for_this_portion * fee_rate
                
                total_fee += fee_for_this_portion
                remaining_to_sell -= shares_from_this_buy
                
                if remaining_to_sell <= 0:
                    break
            
            return total_fee
            
        finally:
            conn.close()

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
                # 只在交易类型不为 'all' 时添加条件
                if filters.get('transaction_type') and filters['transaction_type'] != 'all':
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