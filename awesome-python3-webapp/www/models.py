#!/usr/bin/env python3
# -*- coding:utf-8 -*-
'''
Models for user, blog, comment
'''

__author__ = 'liyy'

import time, uuid
from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    # uuid4()用来随机生成数
    # time.time()返回当前时间
    # 这个函数主要作用就是生成一个和当前时间独一无二的id，来作为数据库表中的每一行的主键
    return '%015d%s00' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'
    # 定义id为主键，调用next_id方法获取默认值
    id = StringField(primary_key=True, default=next_id(), ddl='varchar(50)')
    # 邮箱
    email = StringField(ddl='varchar(50)')
    # 密码
    passwd = StringField(ddl='varchar(50)')
    # 管理员身份，值为1表示用户为管理员，值为0表示用户不是管理员
    admin = BooleanField()
    # 名字
    name = StringField(ddl='varchar(50)')
    # 头像
    image = StringField(ddl='varchar(500)')
    # 创建时间默认为当前时间
    created_at = FloatField(default=time.time())

class Blog(Model):
    __table__ = 'blogs'
    id = StringField(primary_key=True, default=next_id(), ddl='varchar(50)')
    # 作者id
    user_id = StringField(ddl='varchar(50)')
    # 作者名
    user_name = StringField(ddl='varchar(50)')
    # 作者上传的图像
    user_image = StringField(ddl='varchar(500)')
    # 文章名
    name = StringField(ddl='varchar(50)')
    # 文章摘要
    summary = StringField(ddl='varchar(200)')
    # 文章正文
    content = TextField()
    # 创建时间
    created_at = FloatField(default=time.time())

class Comment(Model):
    __table__ = 'comments'
    id = StringField(primary_key=True, default=next_id(), ddl='varchar(50)')
    # 博客id
    blog_id = StringField(ddl='varchar(50)')
    # 评论者id
    user_id = StringField(ddl='varchar(50)')
    # 评论者名字
    user_name = StringField(ddl='varchar(50)')
    # 评论者的图像
    user_image = StringField(ddl='varchar(500)')
    # 文章摘要
    summary = StringField(ddl='varchar(200)')
    # 评论正文
    content = TextField()
    # 创建时间
    created_at = FloatField(default=time.time())