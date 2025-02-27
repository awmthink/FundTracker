import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import json
import re

def get_stock_price_average_eastmoney(stock_code='00020', year=2024, month=12):
    """
    使用东方财富网API获取指定股票在特定年月的每天收盘价格的平均值
    
    Args:
        stock_code: 股票代码，默认为商汤科技 00020
        year: 年份，默认为2024
        month: 月份，默认为12
    
    Returns:
        float: 该月收盘价格的平均值
    """
    # 构建完整的股票代码（港股格式）
    secid = f"116.{stock_code}"  # 东方财富网的港股代码格式 (116是港股前缀)
    
    # 计算开始和结束日期
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # 转换为字符串格式 YYYY-MM-DD
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # 东方财富网历史数据API
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    
    params = {
        'secid': secid,
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': '101',  # 日K线
        'fqt': '0',    # 不复权
        'beg': start_str.replace('-', ''),
        'end': end_str.replace('-', ''),
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'cb': 'jQuery112406471747772220486_' + str(int(time.time() * 1000))
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://quote.eastmoney.com/',
        'Connection': 'keep-alive'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP错误: 状态码 {response.status_code}")
            return None
            
        # 处理JSONP格式的响应
        text = response.text
        json_str = re.search(r'jQuery[0-9_]+\((.*)\)', text)
        
        if not json_str:
            print("无法解析JSONP响应")
            return None
            
        data = json.loads(json_str.group(1))
        
        if data.get('data') and data['data'].get('klines'):
            klines = data['data']['klines']
            
            if not klines:
                print(f"获取的数据为空，可能是非交易日或股票代码错误")
                return None
            
            # 解析K线数据 (格式: "日期,开盘价,收盘价,最高价,最低价,成交量,成交额,振幅,涨跌幅,涨跌额,换手率")
            close_prices = []
            for kline in klines:
                parts = kline.split(',')
                if len(parts) >= 3:  # 确保有收盘价
                    close_prices.append(float(parts[2]))
            
            if not close_prices:
                print(f"获取的数据为空，可能是非交易日或股票代码错误")
                return None
            
            # 计算平均收盘价
            avg_price = sum(close_prices) / len(close_prices)
            
            print(f"{stock_code} (港股) 在 {year}年{month}月的平均收盘价: {avg_price:.4f} HKD")
            return avg_price
        else:
            error_msg = data.get('message', '未知错误')
            print(f"无法获取股票数据: {error_msg}")
            return None
    
    except Exception as e:
        print(f"获取股票数据时出错: {str(e)}")
        return None


if __name__ == "__main__":
    # 获取商汤科技 (00020) 在2024年12月的平均收盘价
    # 尝试使用东方财富网API
    result = get_stock_price_average_eastmoney()

