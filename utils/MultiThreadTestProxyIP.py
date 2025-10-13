# -*- coding = utf-8 -*-
import json
import logging
import os
import sys
import traceback
from datetime import datetime
import threading
import requests
import time
import queue
import re

from lxml import etree

from .check_proxy_ip import check_proxy_ip

# 获取当前文件名
filename = os.path.basename(__file__)
# 获取当前时间并格式化
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
# 创建日志文件名
log_filename = f"{filename}_{current_time}.log"

# 设置日志记录器
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')
ip_port_dict = {}

headers = {
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.33'
}


def get_proxy_ip(page=1):
    # 创建一个线程来运行get_proxy_ip_89ip函数
    thread = threading.Thread(target=get_proxy_ip_89ip, args=(page,))
    thread.start()

    # 在主线程中按顺序调用get_proxy_ip_kuaidaili函数
    get_proxy_ip_kuaidaili('https://www.kuaidaili.com/free/inha/', page)
    get_proxy_ip_kuaidaili('https://www.kuaidaili.com/free/intr/', page)

    # 等待get_proxy_ip_89ip函数的线程完成
    thread.join()


def get_proxy_ip_89ip(page=1):
    if page == 1:
        url = 'https://www.89ip.cn/'
    else:
        url = f'https://www.89ip.cn/index_{page}.html'
    logging.info('getting proxy ip from ' + url + '...')
    response = requests.get(url=url, headers=headers)
    tree = etree.HTML(response.text)  # type: ignore # 加载html文件
    ip_list = tree.xpath('//div[@class="layui-form"]//tr/td[1]/text()')
    port_list = tree.xpath('//div[@class="layui-form"]//tr/td[2]/text()')
    for ip, port in zip(ip_list, port_list):
        ip = str(ip).strip()
        port = str(port).strip()
        logging.info(f'{ip:<18}:{port:>6}')
        ip_port_dict[ip] = port


def get_proxy_ip_kuaidaili(url, page=1):
    # 高匿开放
    if page != 1:
        url = url + str(page)
    logging.info('getting proxy ip from ' + url + ' ...')
    response = requests.get(url=url, headers=headers)
    # 设置编码格式
    response.encoding = 'utf-8'
    # 准备匹配规则
    rule = r'"ip": "(.*?)".*?"port": "(.*?)"'  # 忽略了：后的空格让我找了半天
    # 根据规则匹配数据，匹配到的形式是：[(ip,port),(ip,port),...,(ip,port)]
    match_list = re.findall(rule, response.text, re.S)
    for ip, port in match_list:
        ip = str(ip).strip()
        port = str(port).strip()
        logging.info(f'{ip:<18}:{port:>6}')
        ip_port_dict[ip] = port


class TestProxy(threading.Thread):
    # 定义线程
    def __init__(self, name, q):
        threading.Thread.__init__(self)
        # 线程名称
        self.name = name
        # 队列
        self.q = q

    def run(self):
        # 开始线程
        logging.info("Starting " + self.name)
        while self.q.empty() is False:
            try:
                # 执行crawl耗时操作
                ip = self.q.get()
                logging.info(self.name + '开始测试' + str(ip) + ' ...')
                check_proxy_ip(ip, ip_port_dict[ip])
            except Exception as e:
                logging.error(traceback.format_exc())
        # 退出线程
        logging.info(self.name + " 结束。")


def main(page=0):
    start = time.time()
    logging.error(f'第{page}次获取代理IP...')

    if page == 0:
        # 检查是否有足够的命令行参数
        if len(sys.argv) < 2:
            logging.error("Usage: python temp.py <users_json>")
            sys.exit(1)

        # 从命令行参数中获取users的JSON字符串
        page = int(sys.argv[1])

    get_proxy_ip(page)

    q = queue.Queue(len(ip_port_dict.keys()))
    for url in ip_port_dict.keys():
        q.put(url)

    threads = []
    for i in range(0, 1):
        # 创建12个新线程
        thread = TestProxy(name="Thread-" + str(i+1), q=q)
        # 开启新线程
        thread.start()
        # 添加新线程到线程列表
        threads.append(thread)

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    logging.info(ip_port_dict)

    end = time.time()
    logging.info(f"第{page}次多线程验证代理IP耗时：{end - start} s")
    return ip_port_dict


def write_proxy(json_data):
    # 确保data目录存在
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    proxy_file = os.path.join(data_dir, 'ip_port_dict.json')
    with open(proxy_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
    
    logging.info(f"代理数据已保存到: {proxy_file}")

if __name__ == "__main__":
    page = 1
    json_data = {}
    while len(json_data.keys()) < 3:
        new_json_data = main(page)
        json_data.update(new_json_data)  # 合并json_data和new_json_data
        write_proxy(json_data)
        if page >= 3:
            logging.error(f'{page}次获取代理IP数量仍不足，程序退出')
            break
        page += 1
        logging.error('代理IP数量不足，重试一次')
