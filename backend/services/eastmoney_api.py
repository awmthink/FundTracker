"""东方财富基金数据接口模块

此模块提供了从东方财富网获取基金数据的功能，包括基金基本信息、实时估值和历史净值等。

Author: Your Name
Date: 2024
"""

from typing import Dict, Optional, Any
import requests
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dataclasses import dataclass

# 常量配置
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

FUND_INFO_URL = "http://fund.eastmoney.com/{}.html"
FUND_ESTIMATE_URL = "https://fundgz.1234567.com.cn/js/{}.js"
FUND_HISTORY_URL = "http://api.fund.eastmoney.com/f10/lsjz"


@dataclass
class FundInfo:
    """基金基本信息数据类"""

    code: str
    name: str = ""
    type: str = ""
    purchase_fee: str = ""
    manager: str = ""
    scale: str = ""
    establish_date: str = ""
    risk_level: str = ""
    company: str = ""


def get_fund_info(fund_code: str) -> Dict[str, str]:
    """获取基金的基本信息

    Args:
        fund_code: 基金代码，如'000001'

    Returns:
        包含基金基本信息的字典

    Raises:
        requests.RequestException: 请求失败时抛出
    """
    result = FundInfo(code=fund_code).__dict__

    try:
        response = requests.get(
            FUND_INFO_URL.format(fund_code), headers=BASE_HEADERS, timeout=10
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        # 解析基金名称
        if name_element := soup.find("div", {"class": "fundDetail-tit"}):
            name = name_element.text.strip()
            name = re.sub(r"\([^)]*\)", "", name)
            name = re.sub(r"\s*\d+\s*$", "", name)
            result["name"] = name.strip()

        # 解析基金详细信息
        if info_div := soup.find("div", {"class": "infoOfFund"}):
            _parse_fund_info_div(info_div, result)

        # 解析申购费用
        if fee_item := soup.find(
            "span", {"class": "itemTit"}, string=lambda t: t and "购买手续费" in t
        ):
            if fee_value := fee_item.parent.find("span", {"class": "nowPrice"}):
                fee_text = fee_value.text.strip()
                # 移除百分号并转换为浮点数
                try:
                    fee = float(fee_text.replace("%", "")) / 100
                    result["purchase_fee"] = fee
                except (ValueError, TypeError):
                    result["purchase_fee"] = 0

        return _clean_fund_info(result)

    except requests.RequestException as e:
        print(f"获取基金信息失败: {e}")
        return result


def _parse_fund_info_div(info_div: BeautifulSoup, result: Dict[str, str]) -> None:
    """解析基金信息div中的数据"""
    if table := info_div.find("table"):
        for row in table.find_all("tr"):
            for cell in row.find_all("td"):
                text = cell.text.strip()

                if "类型：" in text:
                    _parse_fund_type(text, result)
                elif "规模" in text:
                    _parse_fund_scale(text, result)
                elif "基金经理：" in text:
                    if manager_link := cell.find("a"):
                        result["manager"] = manager_link.text.strip()
                elif "管 理 人" in text:
                    if company_link := cell.find("a"):
                        result["company"] = company_link.text.strip()
                elif "成 立 日" in text:
                    result["establish_date"] = text.replace("成 立 日：", "").strip()


def _parse_fund_type(text: str, result: Dict[str, str]) -> None:
    """解析基金类型信息"""
    type_text = text.replace("类型：", "").strip()
    if "|" in type_text or "｜" in type_text:
        type_text = type_text.replace("｜", "|")
        type_parts = type_text.split("|")
        result["type"] = type_parts[0].strip()
        if len(type_parts) > 1:
            result["risk_level"] = type_parts[1].strip()
    else:
        result["type"] = type_text


def _parse_fund_scale(text: str, result: Dict[str, str]) -> None:
    """解析基金规模信息"""
    scale_text = text.replace("规模：", "").strip()
    result["scale"] = (
        scale_text.split("（")[0].strip() if "（" in scale_text else scale_text
    )


def _clean_fund_info(data: Dict[str, str]) -> Dict[str, str]:
    """清理基金信息数据"""
    return {
        key: re.sub(r"\s+", " ", str(value)).replace("\xa0", "").strip()
        for key, value in data.items()
    }


def get_fund_estimate(fund_code: str) -> Optional[Dict[str, str]]:
    """获取基金的实时估值信息

    Args:
        fund_code: 基金代码

    Returns:
        包含基金实时估值的字典，如果获取失败返回None
    """
    try:
        response = requests.get(
            FUND_ESTIMATE_URL.format(fund_code), headers=BASE_HEADERS, timeout=10
        )

        if response.status_code == 200:
            if json_match := re.search(r"\((.+)\)", response.text):
                estimate_data = json.loads(json_match.group(1))
                return {
                    "code": estimate_data.get("fundcode", ""),
                    "name": estimate_data.get("name", ""),
                    "estimate_value": estimate_data.get("gsz", ""),
                    "estimate_change": f"{estimate_data.get('gszzl', '')}%",
                    "estimate_time": estimate_data.get("gztime", ""),
                    "last_netvalue": estimate_data.get("dwjz", ""),
                    "last_netvalue_date": estimate_data.get("jzrq", ""),
                }

        # 获取最近的历史净值
        today = datetime.now().strftime("%Y-%m-%d")
        if history_data := get_fund_history_netvalue(fund_code, today):
            fund_info = get_fund_info(fund_code)
            return {
                "code": fund_code,
                "name": fund_info.get("name", ""),
                "estimate_value": "",
                "estimate_change": "",
                "estimate_time": "",
                "last_netvalue": history_data["unit_value"],
                "last_netvalue_date": history_data["date"],
            }

        return None

    except Exception as e:
        print(f"获取基金估值信息失败: {e}")
        return None


def get_fund_history_netvalue(
    fund_code: str, target_date: str
) -> Optional[Dict[str, str]]:
    """获取基金在指定日期的净值数据

    Args:
        fund_code: 基金代码
        target_date: 目标日期，格式：YYYY-MM-DD

    Returns:
        包含净值数据的字典，如果没有找到数据返回None
    """
    try:
        start_date = (
            datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=15)
        ).strftime("%Y-%m-%d")

        params = {
            "fundCode": fund_code,
            "pageIndex": 1,
            "pageSize": 20,
            "startDate": start_date,
            "endDate": target_date,
        }

        headers = {
            **BASE_HEADERS,
            "Referer": f"http://fund.eastmoney.com/f10/jjjz_{fund_code}.html",
        }

        response = requests.get(
            FUND_HISTORY_URL, headers=headers, params=params, timeout=10
        )
        response.raise_for_status()

        history_data = response.json()
        if not (history_list := history_data.get("Data", {}).get("LSJZList")):
            return None

        df = pd.DataFrame(history_list)
        if df.empty:
            return None

        df = df.rename(
            columns={
                "FSRQ": "date",
                "DWJZ": "unit_value",
                "LJJZ": "cumulative_value",
                "JZZZL": "daily_growth",
            }
        )

        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date", ascending=False)

        target_datetime = pd.to_datetime(target_date)
        result_df = df[df["date"] <= target_datetime].head(1)

        if result_df.empty:
            return None

        result_df["date"] = result_df["date"].dt.strftime("%Y-%m-%d")
        return result_df[
            ["date", "unit_value", "cumulative_value", "daily_growth"]
        ].to_dict("records")[0]

    except Exception as e:
        print(f"获取基金历史净值失败: {e}")
        return None


def main():
    """主函数，用于测试"""
    fund_code = input("请输入基金代码: ")

    # 获取基金基本信息
    if fund_info := get_fund_info(fund_code):
        print("\n基金基本信息:")
        for key, value in fund_info.items():
            if value:
                print(f"{key}: {value}")

    # 获取基金实时估值
    if estimate_info := get_fund_estimate(fund_code):
        print("\n基金实时估值信息:")
        print(f"当前估值: {estimate_info['estimate_value']}")
        print(f"估值涨跌: {estimate_info['estimate_change']}")
        print(f"估值时间: {estimate_info['estimate_time']}")
        print(
            f"上一净值: {estimate_info['last_netvalue']} "
            f"({estimate_info['last_netvalue_date']})"
        )
    else:
        print("\n获取实时估值信息失败")

    # 获取过去7天的净值数据
    print("\n过去7天的净值数据:")
    today = datetime.now()
    for i in range(7):
        target_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if netvalue := get_fund_history_netvalue(fund_code, target_date):
            print(
                f"{netvalue['date']}: 单位净值 {netvalue['unit_value']}, "
                f"日增长率 {netvalue['daily_growth']}%"
            )


if __name__ == "__main__":
    main()
