# -*- coding: utf-8 -*-

import os
import sys
sys.path.insert(0, '../util')
import uuid
import time
import pickle
import socket
import logging

from kazoo.client import KazooClient
from kazoo.exceptions import NodeExistsError

from volumn import Volumn

import ip_util

# 获取logger实例，如果参数为空则返回root logger
logger = logging.getLogger()

# 指定logger输出格式
formatter = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s')

# 文件日志
file_handler = logging.FileHandler("volumn.log")
file_handler.setFormatter(formatter)  # 可以通过setFormatter指定输出格式

# 控制台日志
console_handler = logging.StreamHandler(sys.stdout)
console_handler.formatter = formatter  # 也可以直接给formatter赋值

# 为logger添加的日志处理器
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 指定日志的最低输出级别，默认为WARN级别
logger.setLevel(logging.INFO)

config = dict()

if os.path.isfile('config'):
    config = pickle.load(open('config', 'rb'))
else:
    config['id'] = uuid.uuid4().hex
    pickle.dump(config, open('config', 'wb'))

zkServs = ['10.60.45.60', '10.60.45.61', '10.60.45.63']

while True:
    index = 0
    zk = KazooClient(hosts=zkServs[index])
    try:
        zk.start()
        break
    except:
        index = (index + 1) % 3
        continue

def get_free_tcp_port():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port

host = ip_util.find_ip('eth1')
port = get_free_tcp_port()
volumn = Volumn(logger, host, port)

@zk.ChildrenWatch('/master')
def on_volumn_change(children):
    event = []
    for child in children:
        data, _ = zk.get('/master/%s' % child)
        event.append(data.decode())
    volumn.update_master(event)


def main():
    zk.start()

    while True:
        try:
            zk.create('/volumn/%s' % config['id'], ('http://%s:%d' % (host, port)).encode(), ephemeral=True, makepath=True)
            logger.info('Registered in zookeeper')
            break
        except NodeExistsError as e:
            logger.warn('Node exists. Retry after 1s...')
            time.sleep(1)

    volumn.start()

if __name__ == '__main__':
    main()
