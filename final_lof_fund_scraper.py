#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LOF基金数据爬虫和监控系统
支持GitHub Actions环境运行
"""

import requests
from bs4 import BeautifulSoup
import re
import configparser
import json
from datetime import datetime
import os
import time
import random

# 导入基金限额获取模块
FUND_LIMIT_AVAILABLE = False
get_fund_limit = None
try:
    from fund_limit_fetcher import get_fund_limit
    FUND_LIMIT_AVAILABLE = True
    print("成功导入基金限额获取模块")
except ImportError as e:
    print(f"警告: 无法导入基金限额获取模块: {e}")
    print("将使用简化版本的限额获取功能")


def scrape_lof_fund_data():
    """
    采集LOF基金数据并以表格形式呈现
    """
    url = "https://www.palmmicro.com/woody/res/lofcn.php"
    
    try:
        # 发送HTTP请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取基金基本信息表格数据
        fund_basic_data = []
        fund_valuation_data = []
        
        # 处理第一个表格（基金基本信息）
        # 查找id为"referencetable"的表格
        reference_table = soup.find('table', {'id': 'referencetable'})
        if reference_table:
            rows = reference_table.find_all('tr')
            for row in rows[1:]:  # 跳过表头
                cols = row.find_all('td')
                # 检查是否是基金基本信息行（至少6列）
                if len(cols) >= 6:
                    code = cols[0].get_text(strip=True)
                    # 验证是否是有效的基金代码格式
                    if (code.startswith('SH') or code.startswith('SZ')) and len(code) >= 6:
                        fund_basic_data.append({
                            '代码': code,
                            '价格': cols[1].get_text(strip=True),
                            '涨幅': cols[2].get_text(strip=True),
                            '日期': cols[3].get_text(strip=True),
                            '时间': cols[4].get_text(strip=True),
                            '名称': cols[5].get_text(strip=True)
                        })
        
        # 处理第二个表格（基金估值信息）
        # 查找id为"estimationtable"的表格
        estimation_table = soup.find('table', {'id': 'estimationtable'})
        if estimation_table:
            rows = estimation_table.find_all('tr')
            for row in rows[1:]:  # 跳过表头
                cols = row.find_all('td')
                if len(cols) >= 4:  # 至少需要代码、官方估值、估值日期、溢价
                    code = cols[0].get_text(strip=True)
                    # 验证是否是有效的基金代码格式
                    if (code.startswith('SH') or code.startswith('SZ')) and len(code) >= 6:
                        valuation_entry = {
                            '代码': code,
                            '官方估值': cols[1].get_text(strip=True),
                            '估值日期': cols[2].get_text(strip=True),
                            '溢价': cols[3].get_text(strip=True),
                            '参考估值': '',
                            '参考溢价': '',
                            '实时估值': '',
                            '实时溢价': ''
                        }
                        
                        # 根据列数填充额外字段
                        if len(cols) >= 6:  # 有参考估值和参考溢价
                            valuation_entry['参考估值'] = cols[4].get_text(strip=True)
                            valuation_entry['参考溢价'] = cols[5].get_text(strip=True)
                        
                        if len(cols) >= 8:  # 有实时估值和实时溢价
                            valuation_entry['实时估值'] = cols[6].get_text(strip=True)
                            valuation_entry['实时溢价'] = cols[7].get_text(strip=True)
                            
                        fund_valuation_data.append(valuation_entry)
        
        return fund_basic_data, fund_valuation_data
        
    except Exception as e:
        print(f"数据采集过程中出现错误: {e}")
        return [], []


def get_best_valuation_premium(fund_valuation):
    """
    根据优先级获取最佳估值溢价率和估值方式
    优先级：参考估值 > 实时估值 > 官方估值
    
    Args:
        fund_valuation (dict): 基金估值信息
        
    Returns:
        tuple: (premium_rate, valuation_type)
    """
    # 检查参考估值
    if fund_valuation.get('参考溢价') and fund_valuation['参考溢价'].strip():
        return fund_valuation['参考溢价'], '参考'
    
    # 检查实时估值
    if fund_valuation.get('实时溢价') and fund_valuation['实时溢价'].strip():
        return fund_valuation['实时溢价'], '实时'
    
    # 使用官方估值
    if fund_valuation.get('溢价') and fund_valuation['溢价'].strip():
        return fund_valuation['溢价'], '官方'
    
    return '', ''


def send_wechat_notification(message, webhook_url, webhook_key):
    """
    通过企业微信 webhook 发送通知
    
    Args:
        message (str): 要发送的消息内容
        webhook_url (str): webhook URL
        webhook_key (str): webhook key
    """
    # 打印消息内容用于调试
    print("=== 企业微信推送内容 ===")
    print(message)
    print("=== 推送内容结束 ===")
    
    try:
        # 构造完整的 webhook URL
        full_url = f"{webhook_url}?key={webhook_key}"
        
        # 构造消息数据
        data = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        
        # 发送 POST 请求
        headers = {'Content-Type': 'application/json'}
        response = requests.post(full_url, data=json.dumps(data), headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("errcode") == 0:
                print("企业微信通知发送成功")
            else:
                print(f"企业微信通知发送失败: {result.get('errmsg')}")
        else:
            print(f"企业微信通知发送失败，HTTP状态码: {response.status_code}")
    except Exception as e:
        print(f"发送企业微信通知时出错: {e}")


def load_config():
    """
    加载配置文件
    
    Returns:
        dict: 配置项字典
    """
    config = configparser.ConfigParser()
    
    # 获取脚本所在的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    
    # 如果配置文件不存在，尝试打印警告
    if not os.path.exists(config_path):
        print(f"警告: 找不到配置文件 {config_path}，将使用默认配置")
    
    config.read(config_path, encoding='utf-8')
    
    # 获取企业微信配置
    webhook_url = config.get('WeChat', 'webhook_url', fallback='https://qyapi.weixin.qq.com/cgi-bin/webhook/send')
    webhook_key = config.get('WeChat', 'webhook_key', fallback='')
    
    # 获取基金预警配置
    premium_threshold = config.getfloat('FundAlert', 'premium_threshold', fallback=5.0)
    
    # 在GitHub Actions环境中，可以从环境变量获取webhook_key
    if not webhook_key and 'WECHAT_WEBHOOK_KEY' in os.environ:
        webhook_key = os.environ['WECHAT_WEBHOOK_KEY']
    
    return {
        'webhook_url': webhook_url,
        'webhook_key': webhook_key,
        'premium_threshold': premium_threshold
    }


def load_fund_limits_config():
    """
    加载基金限额预定义配置
    
    Returns:
        dict: 基金代码到限额信息的映射
    """
    fund_limits = {}
    try:
        config = configparser.ConfigParser()
        
        # 获取脚本所在的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'fund_limits.ini')
        
        if not os.path.exists(config_path):
            return fund_limits
            
        config.read(config_path, encoding='utf-8')
        
        # 遍历所有基金配置
        for section in config.sections():
            # 跳过注释部分
            if section.startswith('#') or section.startswith(';'):
                continue
            if config.has_option(section, 'limit'):
                fund_limits[section] = config.get(section, 'limit')
                
        print(f"成功加载 {len(fund_limits)} 个基金的预定义限额信息")
    except Exception as e:
        print(f"加载基金限额配置文件时出错: {e}")
    
    return fund_limits


def generate_and_save_fund_summary():
    """
    生成基金信息汇总表并保存到文件
    """
    try:
        # 加载基金限额预定义配置
        fund_limits_config = load_fund_limits_config()
        
        # 获取基金数据
        fund_basic_data, fund_valuation_data = scrape_lof_fund_data()
        
        if not fund_basic_data and not fund_valuation_data:
            print("未能获取到基金数据")
            return
        
        # 创建基金代码到基本信息的映射
        fund_basic_dict = {fund['代码']: fund for fund in fund_basic_data}
        
        # 创建基金代码到估值信息的映射
        fund_valuation_dict = {fund['代码']: fund for fund in fund_valuation_data}
        
        # 加载配置
        config = load_config()
        premium_threshold = config['premium_threshold']
        webhook_url = config['webhook_url']
        webhook_key = config['webhook_key']
        
        # 用于存储高溢价基金的列表
        high_premium_funds = []
        
        # 按代码排序
        all_codes = set(fund_basic_dict.keys()) | set(fund_valuation_dict.keys())
        sorted_codes = sorted(all_codes)
        
        # 用于保存所有基金信息的列表
        all_funds_info = []
        
        # 先收集所有基金的基本信息，但不查询限额
        for code in sorted_codes:
            # 获取基本信息
            basic_info = fund_basic_dict.get(code, {})
            name = basic_info.get('名称', '')
            
            # 获取估值信息
            valuation_info = fund_valuation_dict.get(code, {})
            premium_rate, valuation_type = get_best_valuation_premium(valuation_info)
            
            # 保存基金信息（暂时不查询限额）
            fund_info = {
                'name': name,
                'code': code,
                'premium_rate': premium_rate,
                'valuation_type': valuation_type,
                'limit_info': ''  # 暂时不查询限额
            }
            all_funds_info.append(fund_info)
        
        # 按溢价率排序（从高到低）
        def parse_premium_rate(rate_str):
            try:
                if isinstance(rate_str, str) and rate_str.endswith('%'):
                    return float(rate_str.strip('%'))
                elif rate_str:
                    return float(rate_str)
                else:
                    return 0.0
            except (ValueError, AttributeError):
                return 0.0
        
        all_funds_info.sort(key=lambda x: parse_premium_rate(x['premium_rate']), reverse=True)
        
        # 筛选高溢价基金
        for fund in all_funds_info:
            premium_value = parse_premium_rate(fund['premium_rate'])
            if premium_value >= premium_threshold:
                high_premium_funds.append(fund)
        
        # 只对高溢价基金查询限额信息
        if FUND_LIMIT_AVAILABLE and high_premium_funds:
            print(f"正在查询 {len(high_premium_funds)} 只高溢价基金的限额信息...")
            for fund in high_premium_funds:
                try:
                    # 首先检查是否有预定义的限额信息
                    fund_code = fund['code']
                    if fund_code in fund_limits_config:
                        limit_info = fund_limits_config[fund_code]
                        print(f"基金 {fund_code} 使用预定义限额信息: {limit_info}")
                    else:
                        # 提取纯数字基金代码（去除SH/SZ前缀）
                        pure_fund_code = fund_code
                        if fund_code.startswith('SH') or fund_code.startswith('SZ'):
                            pure_fund_code = fund_code[2:]  # 去除前缀
                        
                        # 增加随机延时，避免请求过于频繁
                        time.sleep(random.uniform(1, 3))
                        limit_info = get_fund_limit(pure_fund_code)
                        print(f"基金 {fund_code} 的限额信息: {limit_info}")
                    
                    fund['limit_info'] = limit_info or '无法获取限额信息'
                except Exception as e:
                    print(f"获取基金 {fund['code']} 限额信息时出错: {e}")
                    fund['limit_info'] = '无法获取限额信息'
        
        # 如果有高溢价基金，发送企业微信通知
        if high_premium_funds:
            # 设计简洁美观的推送消息格式
            message = f"📈 基金溢价预警通知\n"
            message += f"{'─' * 30}\n"
            message += f".threshold: {premium_threshold}%\n"
            message += f".high premium funds: {len(high_premium_funds)} 只\n"
            message += f"{'─' * 30}\n\n"
            
            for i, fund in enumerate(high_premium_funds[:10], 1):  # 最多显示前10只
                limit_info = fund.get('limit_info', '')
                
                message += f"{i}. 📊 {fund['name']} ({fund['code']})\n"
                message += f"   💰 溢价率: {fund['premium_rate']}\n"
                if limit_info:
                    message += f"   🛑 限额: {limit_info}\n"
                else:
                    message += f"   🛑 限额: 无限制\n"
                message += f"\n"
            
            if len(high_premium_funds) > 10:
                message += f"... 还有 {len(high_premium_funds) - 10} 只基金\n\n"
            
            message += f"{'─' * 30}\n"
            # 获取北京时间（UTC+8）
            # 由于GitHub Actions服务器使用UTC时间，需要手动加上8小时转换为北京时间
            from datetime import timedelta
            beijing_time = datetime.utcnow() + timedelta(hours=8)
            message += f"🕒 {beijing_time.strftime('%Y-%m-%d %H:%M')}\n"
            
            send_wechat_notification(message, webhook_url, webhook_key)
        
        # 重新按溢价率排序（从高到低）
        all_funds_info.sort(key=lambda x: parse_premium_rate(x['premium_rate']), reverse=True)
        
    except Exception as e:
        print(f"生成基金信息汇总时出错: {e}")
        import traceback
        traceback.print_exc()


def save_fund_data_to_file():
    """
    将基金数据保存到文件，确保格式正确
    """
    pass


if __name__ == "__main__":
    # 生成并保存基金信息汇总
    generate_and_save_fund_summary()


