import sqlite3
from flask import jsonify
from datetime import datetime, timedelta
import requests
import re
import json
import html
from typing import Optional, Dict, Any
import time


class FundService:
    def __init__(self):
        self.db_name = "finance.db"
        self.base_urls = {
            "fund_info": "http://fund.eastmoney.com/pingzhongdata/{}.js",
            "historical_nav": "http://fund.eastmoney.com/f10/F10DataApi.aspx",
        }
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "http://fund.eastmoney.com/",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
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

    def fetch_fund_info(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """获取基金基本信息，包括名称、净值、估算值和估算增长率"""
        url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js?rt=1589463125600"
        content = self._make_request(url)

        if not content:
            return None

        # Remove the JSONP wrapper
        jsonp_prefix = "jsonpgz("
        jsonp_suffix = ");"
        if content.startswith(jsonp_prefix) and content.endswith(jsonp_suffix):
            json_str = content[len(jsonp_prefix) : -len(jsonp_suffix)]
        else:
            print("Invalid JSONP format")
            return None

        try:
            fund_data = json.loads(json_str)
            return {
                "code": fund_data.get("fundcode"),
                "name": fund_data.get("name"),
                "net_value_date": fund_data.get("jzrq"),
                "unit_net_value": fund_data.get("dwjz"),
                "estimated_value": fund_data.get("gsz"),
                "estimated_growth_rate": fund_data.get("gszzl"),
                "estimated_time": fund_data.get("gztime"),
            }
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            return None

    def fetch_current_nav(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """获取基金当前净值，统一读取前1天的净值，如遇周末或公休假日则递归读取上一个工作日的净值"""
        # 最大前向递归次数为10天
        MAX_DAYS_BACK = 10

        # 尝试获取最近10个工作日内的净值
        for days_back in range(1, MAX_DAYS_BACK + 1):
            check_date = (datetime.now() - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )
            historical_nav = self.get_historical_nav(fund_code, check_date)
            if historical_nav:
                return {"nav": historical_nav, "update_time": check_date}

        # 如果历史净值获取失败，直接返回None
        return None

    def get_historical_nav(self, fund_code: str, date: str) -> Optional[float]:
        """获取历史净值"""
        params = {
            "type": "lsjz",
            "code": fund_code,
            "page": 1,
            "per": 1,
            "sdate": date,
            "edate": date,
        }

        content = self._make_request(self.base_urls["historical_nav"], params)
        if not content:
            return None

        pattern = r"<td>(\d{4}-\d{2}-\d{2})</td><td.*?>(.*?)</td>"
        matches = re.findall(pattern, content)

        for date_str, nav_str in matches:
            if date_str == date:
                try:
                    return float(nav_str)
                except ValueError:
                    print(f"NAV conversion failed: {nav_str}")
                    return None

        # 如果没有匹配到数据，直接返回None
        print(f"No historical NAV found for fund {fund_code} on date {date}")
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

    def get_holdings(self, cutoff_date=None):
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
                SELECT f.fund_code, f.fund_name, f.current_nav, f.fund_type, f.last_update_time, f.target_investment, f.investment_strategy,
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
                        "investment_strategy": row["investment_strategy"] or "",
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
                        "target_investment": fund_data["target_investment"],
                        "investment_strategy": fund_data["investment_strategy"],
                    }
                else:
                    # 非货币型基金正常计算
                    # 获取最新净值，优先使用前一天的净值
                    current_nav = fund_data["current_nav"]

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
                        "target_investment": fund_data["target_investment"],
                        "investment_strategy": fund_data["investment_strategy"],
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
                        investment_strategy = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE fund_code = ?
                """,
                    (
                        data["fund_name"],
                        data["buy_fee"],
                        data["fund_type"],
                        data.get("target_investment", 0),
                        data.get("investment_strategy", ""),
                        data["fund_code"],
                    ),
                )
            else:
                # 插入新基金
                cursor.execute(
                    """
                    INSERT INTO funds (fund_code, fund_name, buy_fee, fund_type, target_investment, investment_strategy)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["fund_code"],
                        data["fund_name"],
                        data["buy_fee"],
                        data["fund_type"],
                        data.get("target_investment", 0),
                        data.get("investment_strategy", ""),
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

    def get_fund_fees(self, fund_code):
        """获取指定基金的费率设置"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT buy_fee
                FROM funds
                WHERE fund_code = ?
            """,
                (fund_code,),
            )
            row = cursor.fetchone()
            if row:
                return {"buy_fee": float(row["buy_fee"])}
            return None
        finally:
            conn.close()

    def update_all_navs(self):
        """更新所有基金的最新净值（前一个工作日）"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # 获取所有基金代码
            cursor.execute("SELECT fund_code FROM funds")
            funds = cursor.fetchall()

            updated_count = 0
            for fund in funds:
                fund_code = fund["fund_code"]

                # 尝试获取最新净值
                result = self.fetch_current_nav(fund_code)

                if result:
                    # 更新数据库中的净值
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

            return {"total": len(funds), "updated": updated_count}

        except Exception as e:
            print(f"Error updating all NAVs: {str(e)}")
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
                fund_settings = self.get_fund_fees(data["fund_code"])
                if not fund_settings:
                    raise ValueError("未找到基金费率设置")
                fee = amount * fund_settings["buy_fee"]

            # 计算份额
            shares = amount / nav

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

    def get_fund_type(self, fund_code: str) -> Optional[str]:
        """
        获取基金类型信息
        Args:
            fund_code: 基金代码
        Returns:
            基金类型字符串，如果获取失败返回None
        """
        try:
            # 尝试从天天基金网获取
            for attempt in range(2):  # 最多尝试2次
                try:
                    # 使用天天基金网的API
                    url = f"http://fund.eastmoney.com/{fund_code}.html"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    response.encoding = "utf-8"
                    html_content = response.text

                    # 提取基金类型
                    type_pattern = r"类型：(.*?)(?:\s*\||</td>)"
                    fund_type = re.search(type_pattern, html_content)
                    if not fund_type:
                        # 尝试备用模式
                        type_pattern_alt = (
                            r"<td[^>]*>基金类型：?</td>\s*<td[^>]*>(.*?)</td>"
                        )
                        fund_type = re.search(type_pattern_alt, html_content)
                        if not fund_type:
                            # 再尝试一种模式
                            type_pattern_alt2 = r'<td class="tb_head">基金类型：</td>[\s\S]*?<td[^>]*>(.*?)</td>'
                            fund_type = re.search(type_pattern_alt2, html_content)
                            if not fund_type:
                                if attempt == 0:  # 第一次尝试失败，等待后重试
                                    time.sleep(1)
                                    continue
                                return None

                    fund_type = fund_type.group(1).strip()
                    # 清除类型中的HTML标签
                    fund_type = re.sub(r"<.*?>", "", fund_type)
                    # 解码HTML实体
                    fund_type = html.unescape(fund_type)
                    # 清除多余的空白字符
                    fund_type = re.sub(r"\s+", " ", fund_type).strip()

                    return fund_type

                except requests.RequestException:
                    if attempt == 0:  # 第一次尝试失败，等待后重试
                        time.sleep(1)
                        continue
                    return None

            # 如果所有尝试都失败
            return None
        except Exception as e:
            print(f"获取基金类型失败: {str(e)}")
            return None

    def get_fund_info(self, fund_code: str) -> Dict[str, Any]:
        """
        获取基金的完整信息，包括名称、净值和类型
        Args:
            fund_code: 基金代码
        Returns:
            包含基金信息的字典
        """
        try:
            # 首先检查数据库中是否已有该基金信息
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT fund_name, fund_type FROM funds WHERE fund_code = ?",
                (fund_code,),
            )
            fund_info = cursor.fetchone()

            # 获取最新净值信息
            nav_info = self.fetch_current_nav(fund_code)

            # 准备返回结果
            result = {
                "code": fund_code,
                "name": "",
                "fund_type": "未知",
                "nav": 0,
                "date": "",
            }

            # 如果数据库中有信息，优先使用
            if fund_info and fund_info["fund_name"]:
                result["name"] = fund_info["fund_name"]
                if fund_info["fund_type"]:
                    result["fund_type"] = fund_info["fund_type"]
            # 如果数据库没有信息，使用fetch_fund_info获取
            else:
                fund_basic_info = self.fetch_fund_info(fund_code)
                if fund_basic_info:
                    result["name"] = fund_basic_info.get("name", "")

            # 设置净值信息
            if nav_info:
                result["nav"] = nav_info.get("nav", 0)
                result["date"] = nav_info.get("date", "")
                # 如果数据库中没有名称但API返回了名称
                if not result["name"] and "name" in nav_info and nav_info["name"]:
                    result["name"] = nav_info["name"]

            # 如果仍然没有基金类型，尝试获取
            if result["fund_type"] == "未知":
                fund_type = self.get_fund_type(fund_code)
                if fund_type:
                    result["fund_type"] = fund_type

                    # 如果获取到了类型但数据库中没有，更新数据库
                    if fund_info and not fund_info["fund_type"] and result["name"]:
                        try:
                            cursor.execute(
                                "UPDATE funds SET fund_type = ? WHERE fund_code = ?",
                                (fund_type, fund_code),
                            )
                            conn.commit()
                        except Exception as e:
                            print(f"更新基金类型失败: {str(e)}")
                            conn.rollback()

            conn.close()
            return result
        except Exception as e:
            print(f"获取基金信息失败: {str(e)}")
            # 确保返回基本结构，即使出错
            return {
                "code": fund_code,
                "name": "",
                "fund_type": "未知",
                "nav": 0,
                "date": "",
            }

    def get_all_fund_settings(self):
        """获取所有基金设置"""
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT fund_code, fund_name, buy_fee, fund_type, target_investment, investment_strategy
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
                    "investment_strategy": row["investment_strategy"],
                }
                for row in settings
            ]
        except Exception as e:
            print(f"获取基金设置失败: {str(e)}")
            raise e
        finally:
            conn.close()
