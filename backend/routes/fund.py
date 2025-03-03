from flask import Blueprint, request, jsonify
from services.fund_service import FundService
from functools import wraps

fund_bp = Blueprint('fund', __name__)
fund_service = FundService()

def handle_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400
        except Exception as e:
            print(f"API错误: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    return decorated_function

@fund_bp.route('/transaction', methods=['POST'])
@handle_exceptions
def add_transaction():
    fund_service.add_transaction(request.json)
    return jsonify({
        'status': 'success',
        'message': '交易添加成功'
    })

@fund_bp.route('/holdings', methods=['GET'])
@handle_exceptions
def get_holdings():
    """获取基金持仓信息"""
    holdings = fund_service.get_holdings()
    return jsonify({
        'status': 'success',
        'data': holdings
    })

@fund_bp.route('/update-nav', methods=['POST'])
@handle_exceptions
def update_nav():
    fund_service.update_nav(request.json)
    return jsonify({
        'status': 'success',
        'message': '更新成功'
    })

# 添加一个测试路由
@fund_bp.route('/test', methods=['GET'])
@handle_exceptions
def test():
    return jsonify({
        'status': 'success',
        'message': 'API is working'
    })

@fund_bp.route('/nav/<fund_code>', methods=['GET'])
@handle_exceptions
def get_fund_nav(fund_code):
    """获取基金净值和基本信息"""
    # 使用整合后的方法获取基金信息
    fund_info = fund_service.get_fund_info(fund_code)
    
    # 即使没有完整信息，也返回已获取的部分信息
    return jsonify({
        'status': 'success',
        'data': fund_info
    })

@fund_bp.route('/historical-nav/<fund_code>/<date>', methods=['GET'])
@handle_exceptions
def get_historical_nav(fund_code, date):
    # 直接使用 fund_service 中的方法获取历史净值
    nav = fund_service.get_historical_nav(fund_code, date)
    
    if nav:
        return jsonify({
            'status': 'success',
            'data': {
                'date': date,
                'nav': nav
            }
        })
    else:
        # 如果没有找到历史净值，尝试获取当前净值
        return get_fund_nav(fund_code)

@fund_bp.route('/settings', methods=['GET'])
@handle_exceptions
def get_all_fund_settings():
    """获取所有基金设置"""
    settings = fund_service.get_all_fund_settings()
    return jsonify({
        'status': 'success',
        'data': settings
    })

@fund_bp.route('/settings', methods=['POST'])
@handle_exceptions
def save_fund_settings():
    """保存基金设置"""
    data = request.json
    fund_service.save_fund_settings(data)
    return jsonify({
        'status': 'success',
        'message': '保存成功'
    })

@fund_bp.route('/settings/<fund_code>', methods=['DELETE'])
@handle_exceptions
def delete_fund_settings(fund_code):
    """删除基金设置"""
    fund_service.delete_fund_settings(fund_code)
    return jsonify({
        'status': 'success',
        'message': '删除成功'
    })

@fund_bp.route('/settings/<fund_code>', methods=['GET'])
@handle_exceptions
def get_fund_fees(fund_code):
    """获取指定基金的费率设置"""
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

@fund_bp.route('/current-nav/<fund_code>', methods=['GET'])
@handle_exceptions
def get_current_nav(fund_code):
    """获取基金当前净值"""
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

@fund_bp.route('/update-all-navs', methods=['POST'])
@handle_exceptions
def update_all_navs():
    """更新所有基金的最新净值"""
    result = fund_service.update_all_navs()
    return jsonify({
        'status': 'success',
        'data': result
    })

@fund_bp.route('/transactions', methods=['GET'])
@handle_exceptions
def get_transactions():
    """获取交易记录"""
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

@fund_bp.route('/transaction/<int:transaction_id>', methods=['DELETE'])
@handle_exceptions
def delete_transaction(transaction_id):
    """删除交易记录"""
    fund_service.delete_transaction(transaction_id)
    return jsonify({
        'status': 'success',
        'message': '删除成功'
    })

@fund_bp.route('/transaction/<int:transaction_id>', methods=['PUT'])
@handle_exceptions
def update_transaction(transaction_id):
    """更新交易记录"""
    data = request.get_json()
    fund_service.update_transaction(transaction_id, data)
    return jsonify({
        'status': 'success',
        'message': '更新成功'
    })
