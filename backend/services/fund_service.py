import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from services.eastmoney_api import get_fund_info as api_get_fund_info
from services.eastmoney_api import get_fund_estimate, get_fund_history_netvalue


class FundService:
    def __init__(self):
        self.db_name = "finance.db"

    def fetch_fund_info(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """获取基金基本信息，包括名称、净值、类型等基础信息

        Args:
            fund_code: 基金代码

        Returns:
            包含基金信息的字典，包括：
            - code: 基金代码
            - name: 基金名称
            - fund_type: 基金类型
            - net_value_date: 净值日期
            - unit_net_value: 单位净值
            - buy_fee: 买入费率（如果能获取到）
        """
        # 获取基金估值信息
        estimate_info = get_fund_estimate(fund_code)
        if not estimate_info:
            return None

        # 获取基金详细信息（包括类型等）
        fund_detail = api_get_fund_info(fund_code)

        result = {
            "code": fund_code,
            "name": estimate_info.get("name", ""),
            "fund_type": fund_detail.get("type", "未知") if fund_detail else "未知",
            "net_value_date": estimate_info.get("last_netvalue_date"),
            "unit_net_value": estimate_info.get("last_netvalue"),
            "buy_fee": fund_detail.get("purchase_fee", 0) if fund_detail else 0,
        }

        return result

    def fetch_current_nav(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """获取基金当前净值"""
        estimate_info = get_fund_estimate(fund_code)
        if not estimate_info:
            return None

        # 如果有实时估值，使用估值
        if estimate_info.get("estimate_value"):
            return {
                "nav": estimate_info["estimate_value"],
                "update_time": estimate_info["estimate_time"],
            }
        # 否则使用最新净值
        elif estimate_info.get("last_netvalue"):
            return {
                "nav": estimate_info["last_netvalue"],
                "update_time": estimate_info["last_netvalue_date"],
            }

        return None

    def get_historical_nav(self, fund_code: str, date: str) -> Optional[float]:
        """获取历史净值"""
        nav_data = get_fund_history_netvalue(fund_code, date)
        if nav_data:
            return float(nav_data["unit_value"])
        return None

    def _update_fund_nav(self, fund_code: str, nav: float, update_time: str) -> None:
        """更新基金净值到数据库"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE funds 
                SET current_nav = ?, last_update_time = ? 
                WHERE fund_code = ?
            """,
                (nav, update_time, fund_code),
            )
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
            required_fields = [
                "fund_code",
                "fund_name",
                "transaction_type",
                "amount",
                "nav",
                "fee",
                "shares",
                "transaction_date",
            ]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"缺少必需字段: {field}")

            # 检查基金是否存在，不存在则添加
            cursor.execute(
                """
                INSERT OR IGNORE INTO funds (fund_code, fund_name, current_nav)
                VALUES (?, ?, ?)
            """,
                (data["fund_code"], data["fund_name"], data["nav"]),
            )

            # 直接使用 fund_code 添加交易记录
            cursor.execute(
                """
                INSERT INTO fund_transactions 
                (fund_code, transaction_type, amount, nav, fee, transaction_date, shares)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data["fund_code"],
                    data["transaction_type"],
                    data["amount"],
                    data["nav"],
                    data["fee"],
                    data["transaction_date"],
                    data["shares"],
                ),
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            print(f"添加交易失败: {str(e)}")
            raise
        finally:
            conn.close()

    def get_holdings(self, cutoff_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取基金持仓信息

        Args:
            cutoff_date: 可选，截止日期，格式为YYYY-MM-DD，默认为None表示使用最新数据
        """
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()

            # 如果没有指定截止日期，则使用昨天的日期（排除今天的交易）
            if not cutoff_date:
                cutoff_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            # 构建查询语句，添加截止日期条件
            query = """
                SELECT f.fund_code, f.fund_name, f.current_nav, f.fund_type, f.last_update_time, f.target_investment,
                       t.transaction_type, t.amount, t.nav, t.shares, t.transaction_date
                FROM funds f
                INNER JOIN fund_transactions t ON f.fund_code = t.fund_code
                WHERE t.transaction_date <= ?
                ORDER BY f.fund_code, t.transaction_date
            """

            cursor.execute(query, [cutoff_date])
            transactions = cursor.fetchall()

            # 按基金代码分组
            funds_data = {}
            for row in transactions:
                fund_code = row["fund_code"]
                if fund_code not in funds_data:
                    funds_data[fund_code] = {
                        "fund_code": fund_code,
                        "fund_name": row["fund_name"],
                        "current_nav": row["current_nav"] or 0,
                        "last_update_time": row["last_update_time"],
                        "fund_type": row["fund_type"] or "未知",
                        "target_investment": row["target_investment"] or 0,
                        "transactions": [],
                    }

                funds_data[fund_code]["transactions"].append(
                    {
                        "transaction_type": row["transaction_type"],
                        "amount": row["amount"],
                        "nav": row["nav"],
                        "shares": row["shares"],
                        "transaction_date": row["transaction_date"],
                    }
                )

            # 计算每个基金的持仓信息
            holdings = []
            try:
                total_market_value = sum(
                    fund_data["current_nav"]
                    * sum(
                        tx["shares"]
                        for tx in fund_data["transactions"]
                        if tx["transaction_type"] == "buy"
                    )
                    - sum(
                        tx["shares"]
                        for tx in fund_data["transactions"]
                        if tx["transaction_type"] == "sell"
                    )
                    for fund_data in funds_data.values()
                )
            except Exception as e:
                print(f"计算总市值失败: {str(e)}")
                total_market_value = 0

            for fund_code, fund_data in funds_data.items():
                # 检查是否为货币型基金
                is_money_fund = "货币" in (fund_data["fund_type"] or "")

                total_buy_amount = 0
                total_sell_amount = 0
                total_shares = 0
                total_cost = 0
                total_profit = 0

                # 用于计算最后一次买入和卖出的净值
                last_buy_nav = None
                last_buy_date = None
                last_sell_nav = None
                last_sell_date = None

                # 按时间排序交易记录，确保最后一次交易是最新的
                sorted_transactions = sorted(
                    fund_data["transactions"], key=lambda x: x["transaction_date"]
                )

                for tx in sorted_transactions:
                    if tx["transaction_type"] == "buy":
                        total_buy_amount += tx["amount"]
                        last_buy_nav = tx["nav"]
                        last_buy_date = tx["transaction_date"]
                        if not is_money_fund:
                            total_shares += tx["shares"]
                            total_cost += tx["amount"]
                    elif tx["transaction_type"] == "sell":
                        total_sell_amount += tx["amount"]
                        last_sell_nav = tx["nav"]
                        last_sell_date = tx["transaction_date"]
                        if not is_money_fund:
                            # 计算当前的平均持仓净值
                            avg_cost = (
                                total_cost / total_shares if total_shares > 0 else 0
                            )
                            total_shares -= tx["shares"]
                            # 计算卖出收益
                            sell_value = (
                                tx["shares"] * tx["nav"]
                            )  # 卖出收益 = 卖出份额 * 当前的平均持仓净值
                            sell_cost = tx["shares"] * avg_cost  # 卖出金额
                            total_profit += (
                                sell_value - sell_cost
                            )  # 累积到总收益中 （这里忽略掉卖出时的手续费）
                            total_cost -= sell_cost

                # 货币型基金特殊处理
                if is_money_fund:
                    # 持有市值等于总的买入-总的赎回
                    market_value = total_buy_amount - total_sell_amount

                    # 货币基金特殊处理
                    holding = {
                        "fund_code": fund_code,
                        "fund_name": fund_data["fund_name"],
                        "fund_type": fund_data["fund_type"],
                        "current_nav": 1.0,  # 货币基金净值固定为1
                        "total_shares": market_value,  # 持有份额等于当前持有的市值
                        "avg_cost_nav": 1.0,  # 平均持仓净值=最新持仓净值
                        "cost_amount": market_value,  # 持仓成本=持有市值
                        "market_value": market_value,
                        "holding_profit": 0,  # 持有收益为0
                        "holding_profit_rate": 0,  # 持有收益率为0
                        "total_profit": 0,  # 累计收益为0
                        "last_update_time": fund_data["last_update_time"],
                        "last_buy_nav": last_buy_nav,
                        "last_buy_date": last_buy_date,
                        "last_sell_nav": last_sell_nav,
                        "last_sell_date": last_sell_date,
                        "since_last_buy_rate": 0,  # 货币基金涨幅为0
                        "since_last_sell_rate": 0,  # 货币基金涨幅为0
                        "target_investment": fund_data[
                            "target_investment"
                        ],  # 目标仓位百分比
                        "actual_position": (
                            (market_value / total_market_value * 100)
                            if total_market_value > 0
                            else 0
                        ),  # 实际仓位百分比
                        "daily_growth_rate": 0,  # 货币基金日涨幅为0
                    }
                else:
                    # 非货币型基金正常计算
                    # 获取最新净值，优先使用前一天的净值
                    current_nav = fund_data["current_nav"]

                    # 获取昨天的历史净值用于计算日涨幅
                    yesterday = (datetime.now() - timedelta(days=1)).strftime(
                        "%Y-%m-%d"
                    )
                    yesterday_nav = self.get_historical_nav(fund_code, yesterday)
                    daily_growth_rate = None
                    if yesterday_nav and current_nav:
                        daily_growth_rate = (
                            current_nav - yesterday_nav
                        ) / yesterday_nav

                    market_value = total_shares * current_nav
                    avg_cost_nav = total_cost / total_shares if total_shares > 0 else 0
                    holding_profit = market_value - total_cost
                    holding_profit_rate = (
                        holding_profit / total_cost if total_cost > 0 else 0
                    )

                    # 计算距上次买入涨幅
                    since_last_buy_rate = None
                    if last_buy_nav and current_nav > 0:
                        since_last_buy_rate = (
                            current_nav - last_buy_nav
                        ) / last_buy_nav

                    # 计算距上次卖出涨幅
                    since_last_sell_rate = None
                    if last_sell_nav and current_nav > 0:
                        since_last_sell_rate = (
                            current_nav - last_sell_nav
                        ) / last_sell_nav

                    holding = {
                        "fund_code": fund_code,
                        "fund_name": fund_data["fund_name"],
                        "fund_type": fund_data["fund_type"],
                        "current_nav": current_nav,
                        "total_shares": total_shares,
                        "avg_cost_nav": avg_cost_nav,
                        "cost_amount": total_cost,
                        "market_value": market_value,
                        "holding_profit": holding_profit,
                        "holding_profit_rate": holding_profit_rate,
                        "total_profit": total_profit + holding_profit,
                        "last_update_time": fund_data["last_update_time"],
                        "last_buy_nav": last_buy_nav,
                        "last_buy_date": last_buy_date,
                        "last_sell_nav": last_sell_nav,
                        "last_sell_date": last_sell_date,
                        "since_last_buy_rate": since_last_buy_rate,
                        "since_last_sell_rate": since_last_sell_rate,
                        "target_investment": fund_data[
                            "target_investment"
                        ],  # 目标仓位百分比
                        "actual_position": (
                            (market_value / total_market_value * 100)
                            if total_market_value > 0
                            else 0
                        ),  # 实际仓位百分比
                        "daily_growth_rate": daily_growth_rate,  # 添加日涨幅字段
                    }

                # 只添加有持仓的基金
                if holding["market_value"] > 0:
                    holdings.append(holding)

            return holdings
        except Exception as e:
            print(f"获取持仓信息失败: {str(e)}")
            raise e
        finally:
            conn.close()

    def update_nav(self, data):
        """更新基金净值"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE funds 
                SET current_nav = ?,
                    last_update_time = ?
                WHERE fund_code = ?
            """,
                (data["current_nav"], datetime.now(), data["fund_code"]),
            )

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def save_fund_settings(self, data):
        """保存基金设置"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()

            # 检查基金代码是否存在
            cursor.execute(
                "SELECT * FROM funds WHERE fund_code = ?", (data["fund_code"],)
            )
            fund = cursor.fetchone()

            if fund:
                # 更新现有基金
                cursor.execute(
                    """
                    UPDATE funds 
                    SET fund_name = ?, buy_fee = ?, fund_type = ?, target_investment = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE fund_code = ?
                """,
                    (
                        data["fund_name"],
                        data["buy_fee"],
                        data["fund_type"],
                        data.get("target_investment", 0),
                        data["fund_code"],
                    ),
                )
            else:
                # 插入新基金
                cursor.execute(
                    """
                    INSERT INTO funds (fund_code, fund_name, buy_fee, fund_type, target_investment)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        data["fund_code"],
                        data["fund_name"],
                        data["buy_fee"],
                        data["fund_type"],
                        data.get("target_investment", 0),
                    ),
                )

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"保存基金设置失败: {str(e)}")
            raise ValueError(f"保存基金设置失败: {str(e)}")
        finally:
            conn.close()

    def check_fund_transactions(self, fund_code):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT COUNT(*) as count 
                FROM fund_transactions 
                WHERE fund_code = ?
            """,
                (fund_code,),
            )
            result = cursor.fetchone()
            return result["count"] if result else 0
        finally:
            conn.close()

    def delete_fund_settings(self, fund_code):
        # 先检查是否存在交易记录
        transaction_count = self.check_fund_transactions(fund_code)
        if transaction_count > 0:
            raise ValueError(f"无法删除该基金，存在 {transaction_count} 条相关交易记录")

        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM funds WHERE fund_code = ?", (fund_code,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def update_all_navs(self, fund_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """更新基金的最新净值

        Args:
            fund_codes: 可选，要更新的基金代码列表。如果为None，则更新所有基金

        Returns:
            包含更新结果的字典
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # 获取需要更新的基金列表
            if fund_codes:
                cursor.execute(
                    "SELECT fund_code FROM funds WHERE fund_code IN ({})".format(
                        ",".join("?" * len(fund_codes))
                    ),
                    fund_codes,
                )
            else:
                cursor.execute("SELECT fund_code FROM funds")

            funds = cursor.fetchall()
            updated_count = 0

            for fund in funds:
                fund_code = fund["fund_code"]
                result = self.fetch_current_nav(fund_code)

                if result:
                    cursor.execute(
                        """
                        UPDATE funds 
                        SET current_nav = ?,
                            last_update_time = ?
                        WHERE fund_code = ?
                    """,
                        (result["nav"], result["update_time"], fund_code),
                    )
                    conn.commit()
                    updated_count += 1

            return {
                "total": len(funds),
                "updated": updated_count,
                "failed": len(funds) - updated_count,
            }

        except Exception as e:
            print(f"Error updating NAVs: {str(e)}")
            raise
        finally:
            if "conn" in locals():
                conn.close()

    def get_transactions(self, filters=None):
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            query = """
                SELECT 
                    t.transaction_id,
                    t.fund_code,
                    f.fund_name,
                    t.transaction_type,
                    t.amount,
                    t.nav,
                    t.fee,
                    t.shares,
                    t.transaction_date
                FROM fund_transactions t
                JOIN funds f ON t.fund_code = f.fund_code
                WHERE 1=1
            """
            params = []

            if filters:
                if filters.get("fund_code"):
                    query += " AND f.fund_code LIKE ?"
                    params.append(f"%{filters['fund_code']}%")
                if filters.get("fund_name"):
                    query += " AND f.fund_name LIKE ?"
                    params.append(f"%{filters['fund_name']}%")
                if filters.get("start_date"):
                    query += " AND t.transaction_date >= ?"
                    params.append(filters["start_date"])
                if filters.get("end_date"):
                    query += " AND t.transaction_date <= ?"
                    params.append(filters["end_date"])
                # 只在交易类型不为 'all' 时添加条件
                if (
                    filters.get("transaction_type")
                    and filters["transaction_type"] != "all"
                ):
                    query += " AND t.transaction_type = ?"
                    params.append(filters["transaction_type"])

            query += " ORDER BY t.transaction_date DESC"

            cursor.execute(query, params)
            transactions = cursor.fetchall()

            return [
                {
                    "transaction_id": row["transaction_id"],
                    "fund_code": row["fund_code"],
                    "fund_name": row["fund_name"],
                    "transaction_type": row["transaction_type"],
                    "amount": float(row["amount"]),
                    "nav": float(row["nav"]),
                    "fee": float(row["fee"]),
                    "shares": float(row["shares"]),
                    "transaction_date": row["transaction_date"],
                }
                for row in transactions
            ]

        finally:
            conn.close()

    def delete_transaction(self, transaction_id):
        """删除交易记录"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "DELETE FROM fund_transactions WHERE transaction_id = ?",
                (transaction_id,),
            )
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
            required_fields = [
                "fund_code",
                "fund_name",
                "transaction_type",
                "amount",
                "nav",
                "transaction_date",
            ]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"缺少必需字段: {field}")

            # 确保数值字段为浮点数
            amount = float(data["amount"])
            nav = float(data["nav"])

            # 验证交易记录是否存在
            cursor.execute(
                "SELECT * FROM fund_transactions WHERE transaction_id = ?",
                (transaction_id,),
            )
            if not cursor.fetchone():
                raise ValueError("交易记录不存在")

            # 验证基金是否存在
            cursor.execute(
                "SELECT * FROM funds WHERE fund_code = ?", (data["fund_code"],)
            )
            if not cursor.fetchone():
                raise ValueError("基金不存在")

            # 计算手续费
            if data["transaction_type"] == "sell":
                fee = float(data.get("fee", 0))  # 使用用户输入的手续费
            else:
                # 获取基金费率设置
                fund_settings = self.get_all_fund_settings()
                fund_setting = next(
                    (f for f in fund_settings if f["fund_code"] == data["fund_code"]),
                    None,
                )
                if not fund_setting:
                    raise ValueError("未找到基金费率设置")
                fee = amount * fund_setting["buy_fee"]

            # 计算份额
            shares = (
                amount / nav
                if data["transaction_type"] == "buy"
                else float(data.get("shares", 0))
            )

            # 更新交易记录 - 注意这里不再使用 fund_id
            cursor.execute(
                """
                UPDATE fund_transactions 
                SET transaction_type = ?, 
                    amount = ?, 
                    nav = ?, 
                    fee = ?, 
                    transaction_date = ?, 
                    shares = ?
                WHERE transaction_id = ?
            """,
                (
                    data["transaction_type"],
                    amount,
                    nav,
                    fee,
                    data["transaction_date"],
                    shares,
                    transaction_id,
                ),
            )

            if cursor.rowcount == 0:
                raise ValueError("更新失败，未找到对应的交易记录")

            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"更新交易记录失败: {str(e)}")  # 添加日志输出
            raise e
        finally:
            conn.close()

    def get_fund_info(self, fund_code: str) -> Dict[str, Any]:
        """
        获取基金的完整信息，包括名称、净值、类型和费率
        Args:
            fund_code: 基金代码
        Returns:
            包含基金信息的字典，包括：
            - code: 基金代码
            - name: 基金名称
            - fund_type: 基金类型
            - nav: 最新净值
            - update_time: 净值更新时间
            - buy_fee: 买入费率
        """
        conn = None
        try:
            # 准备返回结果
            result = {
                "code": fund_code,
                "name": "",
                "fund_type": "未知",
                "nav": 0,
                "update_time": "",
                "buy_fee": 0,
            }

            # 首先从数据库获取基本信息
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT fund_name, fund_type, buy_fee FROM funds WHERE fund_code = ?",
                (fund_code,),
            )
            fund_info = cursor.fetchone()

            # 如果数据库中有信息，优先使用
            if fund_info:
                result["name"] = (
                    fund_info["fund_name"] if fund_info["fund_name"] else ""
                )
                result["fund_type"] = (
                    fund_info["fund_type"] if fund_info["fund_type"] else "未知"
                )
                result["buy_fee"] = (
                    float(fund_info["buy_fee"])
                    if fund_info["buy_fee"] is not None
                    else 0
                )

            # 如果数据库中没有完整信息，从API获取
            if not result["name"] or result["fund_type"] == "未知":
                fund_basic_info = self.fetch_fund_info(fund_code)
                if fund_basic_info:
                    # 更新基金信息
                    if not result["name"]:
                        result["name"] = fund_basic_info["name"]
                    if result["fund_type"] == "未知":
                        result["fund_type"] = fund_basic_info["fund_type"]
                    # 如果数据库中没有费率信息，使用API返回的费率
                    if result["buy_fee"] == 0:
                        result["buy_fee"] = fund_basic_info.get("buy_fee", 0)

                    # 更新净值信息
                    result["nav"] = fund_basic_info.get("unit_net_value", 0)
                    result["update_time"] = fund_basic_info.get("net_value_date", "")

            return result

        except Exception as e:
            print(f"获取基金信息失败: {str(e)}")
            # 确保返回基本结构，即使出错
            return {
                "code": fund_code,
                "name": "",
                "fund_type": "未知",
                "nav": 0,
                "update_time": "",
                "buy_fee": 0,
            }
        finally:
            if conn:
                conn.close()

    def get_all_fund_settings(self):
        """获取所有基金设置"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT fund_code, fund_name, buy_fee, fund_type, target_investment
                FROM funds
                ORDER BY fund_code
            """
            )
            settings = cursor.fetchall()
            return [
                {
                    "fund_code": row["fund_code"],
                    "fund_name": row["fund_name"],
                    "buy_fee": float(row["buy_fee"]),
                    "fund_type": row["fund_type"],
                    "target_investment": (
                        float(row["target_investment"])
                        if row["target_investment"] is not None
                        else 0
                    ),
                }
                for row in settings
            ]
        except Exception as e:
            print(f"获取基金设置失败: {str(e)}")
            raise e
        finally:
            conn.close()
