#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基金限额信息获取模块
从天天基金网爬取基金的申购限额和交易状态信息
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random


def get_fund_limit(fund_code):
    """
    从天天基金网获取指定基金的限额信息
    
    Args:
        fund_code (str): 基金代码
        
    Returns:
        str: 限额信息描述，如"单日累计购买上限10.00元"或"暂停申购"等
    """
    try:
        # 构造基金详情页URL
        url = f"https://fund.eastmoney.com/{fund_code}.html?spm=search"
        
        # 设置完整的请求头，模拟真实浏览器访问
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Host': 'fund.eastmoney.com',
            'Referer': f'https://fund.eastmoney.com/{fund_code}.html?spm=search',
            'Sec-Ch-Ua': '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0'
        }
        
        # 发送HTTP请求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        # 检查页面内容是否为空
        if not response.text or len(response.text) < 1000:
            print(f"基金 {fund_code} 页面内容异常，长度: {len(response.text)}")
            # 保存页面内容用于调试
            with open(f'fund_{fund_code}_error.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            return "获取失败"
        
        # 保存页面内容用于调试
        with open(f'fund_{fund_code}_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"基金 {fund_code} 页面已保存用于调试")
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找交易状态信息 - 方法1: 查找包含"交易状态"的span标签
        item_titles = soup.find_all('span', class_='itemTit')
        print(f"找到 {len(item_titles)} 个 itemTit 元素")
        for item_tit in item_titles:
            title_text = item_tit.get_text()
            print(f"itemTit 内容: {title_text}")
            if '交易状态' in title_text:
                print("找到交易状态标题")
                # 找到交易状态的父元素
                parent = item_tit.parent
                if parent:
                    print("找到父元素")
                    # 查找所有staticCell元素
                    static_cells = parent.find_all('span', class_='staticCell')
                    print(f"找到 {len(static_cells)} 个 staticCell 元素")
                    for cell in static_cells:
                        cell_text = cell.get_text()
                        print(f"staticCell 内容: {cell_text}")
                        # 检查是否包含限额信息
                        if '单日累计购买上限' in cell_text:
                            # 提取限额数值
                            limit_match = re.search(r'单日累计购买上限([^\)]+)', cell_text)
                            if limit_match:
                                result = limit_match.group(1)
                                print(f"匹配到限额: {result}")
                                return result
                        elif '限大额' in cell_text:
                            # 处理限大额情况，尝试提取具体金额
                            amount_match = re.search(r'[（(]([^)）]*)[)）]', cell_text)
                            if amount_match:
                                result = amount_match.group(1)
                                print(f"匹配到限大额: {result}")
                                return result
                            else:
                                print("匹配到限大额但无具体金额")
                                return "限大额"
                        elif '暂停申购' in cell_text:
                            print("匹配到暂停申购")
                            return "暂停申购"
        
        # 查找交易状态信息 - 方法2: 直接查找包含限额信息的span标签
        limit_spans = soup.find_all('span', string=re.compile('单日累计购买上限'))
        print(f"找到 {len(limit_spans)} 个包含限额信息的span标签")
        for span in limit_spans:
            text = span.get_text()
            print(f"限额span内容: {text}")
            limit_match = re.search(r'单日累计购买上限([^\)]+)', text)
            if limit_match:
                result = limit_match.group(1)
                print(f"通过方法2匹配到限额: {result}")
                return result
                
        # 查找交易状态信息 - 方法3: 查找包含"限大额"的元素
        limit_elements = soup.find_all(string=re.compile('限大额'))
        print(f"找到 {len(limit_elements)} 个包含限大额的元素")
        for element in limit_elements:
            text = str(element)
            print(f"限大额元素内容: {text}")
            if '单日累计购买上限' in text:
                limit_match = re.search(r'单日累计购买上限([^\)]+)', text)
                if limit_match:
                    result = limit_match.group(1)
                    print(f"通过方法3匹配到限额: {result}")
                    return result
            elif '限大额' in text:
                amount_match = re.search(r'[（(]([^)）]*)[)）]', text)
                if amount_match:
                    result = amount_match.group(1)
                    print(f"通过方法3匹配到限大额: {result}")
                    return result
                else:
                    print("通过方法3匹配到限大额但无具体金额")
                    return "限大额"
        
        # 如果还是找不到，返回默认值
        print("未找到任何限额信息")
        return "无限制"
        
    except Exception as e:
        print(f"获取基金 {fund_code} 限额信息时出错: {e}")
        return "获取失败"


def is_fund_limited(fund_code):
    """
    判断基金是否处于限购状态
    
    Args:
        fund_code (str): 基金代码
        
    Returns:
        bool: True表示限购，False表示不限购
    """
    limit_info = get_fund_limit(fund_code)
    
    # 定义表示限购的关键词
    limited_keywords = ['暂停申购', '限大额', '单日累计购买上限']
    
    for keyword in limited_keywords:
        if keyword in limit_info:
            return True
            
    return False


# 测试函数
if __name__ == "__main__":
    # 测试获取指定基金的限额信息
    test_fund_code = "161128"  # 易方达标普信息科技指数(QDII-LOF)A
    limit_info = get_fund_limit(test_fund_code)
    print(f"基金 {test_fund_code} 的限额信息: {limit_info}")
    
    is_limited = is_fund_limited(test_fund_code)
    print(f"基金 {test_fund_code} 是否限购: {is_limited}")