from flask import Blueprint, request, jsonify
from services.fund_service import FundService
from functools import wraps

fund_bp = Blueprint("fund", __name__)
fund_service = FundService()


def handle_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            print(f"API错误: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

    return decorated_function


# 基金基本信息接口
@fund_bp.route("/funds/<fund_code>", methods=["GET"])
@handle_exceptions
def get_fund_info(fund_code):
    """获取基金基本信息"""
    fund_info = fund_service.get_fund_info(fund_code)
    return jsonify({"status": "success", "data": fund_info})


# 净值相关接口
@fund_bp.route("/nav/<fund_code>", methods=["GET", "POST"])
@handle_exceptions
def handle_fund_nav(fund_code):
    """处理基金净值的获取和更新

    GET: 获取基金当前净值
    POST: 更新基金净值
    """
    if request.method == "GET":
        nav_info = fund_service.fetch_current_nav(fund_code)
        if nav_info:
            return jsonify({"status": "success", "data": nav_info})
        return jsonify({"status": "error", "message": "获取净值失败"}), 404
    else:  # POST
        data = request.get_json()
        data["fund_code"] = fund_code  # 确保使用URL中的fund_code
        fund_service.update_nav(data)
        return jsonify({"status": "success", "message": "更新成功"})


@fund_bp.route("/nav/<fund_code>/history/<date>", methods=["GET"])
@handle_exceptions
def get_historical_nav(fund_code, date):
    """获取指定日期的基金净值"""
    nav = fund_service.get_historical_nav(fund_code, date)
    if nav:
        return jsonify({"status": "success", "data": {"date": date, "nav": nav}})
    return jsonify({"status": "error", "message": "未找到该日期的净值数据"}), 404


@fund_bp.route("/nav/batch/update", methods=["POST"])
@handle_exceptions
def update_navs():
    """批量更新基金净值

    如果请求体中包含 fund_codes 列表，则只更新指定基金
    否则更新所有基金
    """
    data = request.get_json()
    if data and "fund_codes" in data:
        result = fund_service.update_all_navs(data["fund_codes"])
    else:
        result = fund_service.update_all_navs()
    return jsonify({"status": "success", "data": result})


# 交易相关接口
@fund_bp.route("/transactions", methods=["GET", "POST"])
@handle_exceptions
def handle_transactions():
    """处理交易记录的查询和添加"""
    if request.method == "GET":
        filters = {
            "fund_code": request.args.get("fund_code"),
            "fund_name": request.args.get("fund_name"),
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
            "transaction_type": request.args.get("transaction_type"),
        }
        transactions = fund_service.get_transactions(filters)
        return jsonify({"status": "success", "data": transactions})
    else:  # POST
        fund_service.add_transaction(request.json)
        return jsonify({"status": "success", "message": "交易添加成功"})


@fund_bp.route("/transactions/<int:transaction_id>", methods=["PUT", "DELETE"])
@handle_exceptions
def handle_transaction(transaction_id):
    """处理单个交易记录的更新和删除"""
    if request.method == "PUT":
        fund_service.update_transaction(transaction_id, request.json)
        return jsonify({"status": "success", "message": "更新成功"})
    else:  # DELETE
        fund_service.delete_transaction(transaction_id)
        return jsonify({"status": "success", "message": "删除成功"})


# 基金设置相关接口
@fund_bp.route("/settings", methods=["GET", "POST"])
@handle_exceptions
def handle_settings():
    """处理基金设置的查询和添加"""
    if request.method == "GET":
        settings = fund_service.get_all_fund_settings()
        return jsonify({"status": "success", "data": settings})
    else:  # POST
        fund_service.save_fund_settings(request.json)
        return jsonify({"status": "success", "message": "保存成功"})


@fund_bp.route("/settings/<fund_code>", methods=["GET", "DELETE"])
@handle_exceptions
def handle_fund_settings(fund_code):
    """处理单个基金设置的查询和删除"""
    if request.method == "GET":
        fees = fund_service.get_fund_fees(fund_code)
        if fees:
            return jsonify({"status": "success", "data": fees})
        return jsonify({"status": "error", "message": "未找到该基金的费率设置"}), 404
    else:  # DELETE
        fund_service.delete_fund_settings(fund_code)
        return jsonify({"status": "success", "message": "删除成功"})


# 持仓相关接口
@fund_bp.route("/holdings", methods=["GET"])
@handle_exceptions
def get_holdings():
    """获取基金持仓信息"""
    cutoff_date = request.args.get("cutoff_date")  # 可选参数：截止日期
    holdings = fund_service.get_holdings(cutoff_date)
    return jsonify({"status": "success", "data": holdings})


# 测试路由
@fund_bp.route("/test", methods=["GET"])
@handle_exceptions
def test():
    return jsonify({"status": "success", "message": "API is working"})
