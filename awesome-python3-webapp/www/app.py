#!/usr/bin/env python3
# -*-coding:utf-8-*-
__author__ = 'liyy'
import logging
logging.basicConfig(level=logging.INFO)
# logging作用就是输出一些信息
import asyncio, os, json, time
from datetime import datetime
from aiohttp import web
# 定义处理http访问请求的方法
def index(request):
    # 返回括号内的内容作为web相应
    return web.Response(body=b'<h1>Awesome</h1>')

@asyncio.coroutine
def init(loop):
    # 往web对象中家入消息循环，生产一个异步IO对象
    app = web.Application(loop = loop)
    # 将浏览器通过GET方式传过来的对根目录的请求转发给index函数处理
    app.router.add_route('GET', '/', index)
    # 监听ip和端口
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    # 控制台显示ip和端口信息
    logging.info('sever started at http://127.0.0.1:9000...')
    # 把监听http请求的这个协称返会给loop，这样就能继续监听http请求
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
