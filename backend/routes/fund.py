from flask import Blueprint, request, jsonify
from services.fund_service import FundService
import requests
import re
import json

fund_bp = Blueprint('fund', __name__)
fund_service = FundService()

@fund_bp.route('/transaction', methods=['POST'])
def add_transaction():
    try:
        return fund_service.add_transaction(request.json)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fund_bp.route('/holdings', methods=['GET'])
def get_holdings():
    """获取基金持仓信息"""
    try:
        holdings = fund_service.get_holdings()
        return jsonify({
            'status': 'success',
            'data': holdings
        })
    except Exception as e:
        print(f"Error in get_holdings route: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fund_bp.route('/update-nav', methods=['POST'])
def update_nav():
    try:
        return fund_service.update_nav(request.json)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 添加一个测试路由
@fund_bp.route('/test', methods=['GET'])
def test():
    return jsonify({
        'status': 'success',
        'message': 'API is working'
    })

@fund_bp.route('/nav/<fund_code>', methods=['GET'])
def get_fund_nav(fund_code):
    """获取基金信息"""
    print(f"Received request for fund code: {fund_code}")  # 添加请求日志
    
    try:
        # 首先尝试从数据库获取基金信息
        conn = fund_service.get_db_connection()
        cursor = conn.cursor()
        
        print("Querying database...")  # 添加数据库查询日志
        cursor.execute('''
            SELECT fund_code, fund_name
            FROM fund_settings
            WHERE fund_code = ?
        ''', (fund_code,))
        fund = cursor.fetchone()
        
        if fund:
            print(f"Found fund in database: {fund['fund_name']}")  # 添加数据库结果日志
            return jsonify({
                'status': 'success',
                'data': {
                    'code': fund['fund_code'],
                    'name': fund['fund_name']
                }
            })
            
        print("Fund not found in database, fetching from network...")  # 添加网络请求日志
        # 如果数据库中没有，则从天天基金网获取信息
        fund_info = fund_service.fetch_fund_info(fund_code)
        print(f"Network response: {fund_info}")  # 添加网络响应日志
        
        if fund_info:
            return jsonify({
                'status': 'success',
                'data': fund_info
            })
            
        return jsonify({
            'status': 'error',
            'message': '未找到该基金信息'
        }), 404
        
    except Exception as e:
        import traceback
        print(f"Error getting fund info: {str(e)}")  # 添加错误日志
        print(traceback.format_exc())  # 添加堆栈跟踪
        return jsonify({
            'status': 'error',
            'message': f'获取基金信息失败: {str(e)}'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

@fund_bp.route('/historical-nav/<fund_code>/<date>', methods=['GET'])
def get_historical_nav(fund_code, date):
    try:
        # 使用天天基金的历史净值接口
        url = f'http://api.fund.eastmoney.com/f10/lsjz'
        params = {
            'fundCode': fund_code,
            'pageIndex': 1,
            'pageSize': 1,
            'startDate': date,
            'endDate': date
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': f'http://fundf10.eastmoney.com/jjjz_{fund_code}.html'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return jsonify({
                'status': 'error',
                'message': '获取历史净值数据失败'
            })

        data = response.json()
        
        # 检查返回的数据结构
        if not data.get('Data') or not data['Data'].get('LSJZList'):
            # 如果没有找到历史净值，尝试获取当前净值
            return get_fund_nav(fund_code)

        nav_data = data['Data']['LSJZList'][0]
        
        return jsonify({
            'status': 'success',
            'data': {
                'date': nav_data['FSRQ'],  # 净值日期
                'nav': float(nav_data['DWJZ'])  # 单位净值
            }
        })
        
    except requests.RequestException as e:
        # 如果获取历史净值失败，尝试获取当前净值
        return get_fund_nav(fund_code)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取历史净值失败: {str(e)}'
        })

@fund_bp.route('/settings', methods=['GET'])
def get_all_fund_settings():
    """获取所有基金的费率设置"""
    try:
        cursor = fund_service.get_db_connection().cursor()
        cursor.execute('''
            SELECT fund_code, fund_name, buy_fee, 
                   sell_fee_lt7, sell_fee_lt365, sell_fee_gt365
            FROM fund_settings
        ''')
        settings = cursor.fetchall()
        
        result = []
        for row in settings:
            result.append({
                'fund_code': row['fund_code'],
                'fund_name': row['fund_name'],
                'buy_fee': float(row['buy_fee']),
                'sell_fee_lt7': float(row['sell_fee_lt7']),
                'sell_fee_lt365': float(row['sell_fee_lt365']),
                'sell_fee_gt365': float(row['sell_fee_gt365'])
            })
        
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        print(f"获取基金设置失败: {str(e)}")  # 添加服务器端日志
        return jsonify({
            'status': 'error',
            'message': f'获取基金设置失败: {str(e)}'
        }), 500

@fund_bp.route('/settings', methods=['POST'])
def save_fund_settings():
    """保存基金设置"""
    try:
        data = request.json
        fund_service.save_fund_settings(data)
        return jsonify({
            'status': 'success',
            'message': '保存成功'
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fund_bp.route('/settings/<fund_code>', methods=['DELETE'])
def delete_fund_settings(fund_code):
    """删除基金设置"""
    try:
        fund_service.delete_fund_settings(fund_code)
        return jsonify({
            'status': 'success',
            'message': '删除成功'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fund_bp.route('/settings/<fund_code>', methods=['GET'])
def get_fund_fees(fund_code):
    """获取指定基金的费率设置"""
    try:
        fees = fund_service.get_fund_fees(fund_code)
        if fees:
            return jsonify({
                'status': 'success',
                'data': fees
            })
        return jsonify({
            'status': 'error',
            'message': '未找到该基金的费率设置'
        }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fund_bp.route('/current-nav/<fund_code>', methods=['GET'])
def get_current_nav(fund_code):
    """获取基金当前净值"""
    try:
        nav_info = fund_service.fetch_current_nav(fund_code)
        if nav_info:
            return jsonify({
                'status': 'success',
                'data': nav_info
            })
        return jsonify({
            'status': 'error',
            'message': '获取净值失败'
        }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fund_bp.route('/update-all-navs', methods=['POST'])
def update_all_navs():
    """更新所有基金的最新净值"""
    try:
        result = fund_service.update_all_navs()
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fund_bp.route('/transactions', methods=['GET'])
def get_transactions():
    """获取交易记录"""
    try:
        filters = {
            'fund_code': request.args.get('fund_code'),
            'fund_name': request.args.get('fund_name'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'transaction_type': request.args.get('transaction_type')
        }
        transactions = fund_service.get_transactions(filters)
        return jsonify({
            'status': 'success',
            'data': transactions
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fund_bp.route('/transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """删除交易记录"""
    try:
        fund_service.delete_transaction(transaction_id)
        return jsonify({
            'status': 'success',
            'message': '删除成功'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fund_bp.route('/transaction/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """更新交易记录"""
    try:
        data = request.get_json()
        fund_service.update_transaction(transaction_id, data)
        return jsonify({
            'status': 'success',
            'message': '更新成功'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
