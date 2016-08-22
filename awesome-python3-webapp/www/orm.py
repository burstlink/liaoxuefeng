#!/usr/bin/env python3
# -*- coding:utf-8 -*-

__author__ = 'liyy'

import asyncio, logging, aiomysql
# 下面用到log函数的地方，输出的信息可以知道这个时间点这个程序在干什么
def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# 这个函数将来会在app.py的init函数中引用，目的是为了创建一个全局变量__pool，
# 当需要链接数据库时可以直接从__pool中获取链接
@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool....')
    # 声明全局变量__pool
    global __pool
    __pool = yield from aiomysql.create_pool(
        # kw应该是create_pool函数的参数**kw，也就是关键字参数
        # kw是根据 **kw创建的一个dict
        # kw这个get函数的作用就是当没有传入host参数时就去默认的localhost
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        # dict取值方式
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf-8'),
        # 最大连接数
        maxsize=kw.get('maxsize', 10),
        # 最小连接数
        minsize=kw.get('minsize', 1),
        loop=loop
    )

# 将执行sql的代码封装进select函数，调用的时候只要传入sql，和sql需要的一些参数就好
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    # 声明__pool是一个全局变量，这样才能引用create_pool函数创建的__pool变量
    global __pool
    # 从连接池中获取一个数据库链接
    with (yield from __pool) as conn:
        # conn.cursor相当于命令行输入myqsl -uroot -p 知乎进去数据库中，
        # cur就是那个闪烁的光标
        cur = yield from conn.cursor(aiomysql.DictCursor)
        # cur.execute相当于输入sql语句，然后回车执行
        # sql.replace作用是把SQl的占位符？换成%s，
        # args是执行sql语句时候通过占位符茶余的一些参数
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        # size就是要返会的结果数，如果不传入就默认返回查询结果
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info('row returned: %s' %len(rs))
        return rs

# 基本上和select函数差不多，我就为不一样的地方做下注释
@asyncio.coroutine
def execute(sql, args):
    log(sql)
    # 从连接池去除一个数据库链接
    with (yield from __pool) as conn:
        if not conn.get_autocommit():
            # 若数据库事务不是自动提交则用协程启动连接
            yield from conn.begin()
            # 我猜可能是，不是自动连接数据库就连接数据库的意思
        try:

            cur = yield from conn.cursor()
            # 执行增删改
            yield from cur.execute(sql.replace('?', '%s'), args)
            # affected是受影响的行数，比如说插入一行数据，那受影响行数就是一行
            affected = cur.rowcount
            # 执行结束关闭游标
            yield from cur.close()
            if not conn.get_autocommit():
                # 如果不是自动提交那就手动提交？提交什么，提交到哪儿？猜都没法猜
                yield from conn.commit()
        # 捕获数据库错误，但我不清楚具体是什么错误，为什么select函数不需要捕获？
        except BaseException as e:
            if not conn.get_autocommit():
                # 出错就回滚到增删改之前
                # rollback是回滚的意思
                yield from conn.rollback()
            raise
        return affected
# 这个函数在元类中被引用
# 作用是构造一定数量的占位符
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    # 比如说num=3，那L就是['?','?','?']，通过下面这句代码返回一个字符串'?,?,?'
    return ', '.join(L)


# 定义字段基类（父类），后面各种各样的字段类都继承这个基类
class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name  # 字段名
        self.column_type = column_type  # 字段类型
        self.primary_key = primary_key  # 主键
        self.default = default  # 默认值

    # 元类那节也有一个orm的例子，里面也有这个函数，好像是为了在命令行按照'<%s, %s:%s>'这个格式输出字段的相关信息
    # 注释掉之后会报错，不知道什么原因，估计在哪个地方会用到这个字符串，我暂时还没找到在哪儿
    # 打印信息，依次是类名，属性类型，属性名
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


# 字符串域
class StringField(Field):
    # ddl是数据定义语言("data definition languages")，
    # 默认值是'varchar(100)'，意思是可变字符串，长度为100
    # 和char相对应，char是固定长度，字符串长度不够会自动补齐，
    # varchar则是多长就是多长，但最长不能超过规定长度
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

# 布尔域
class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

# 整数域
class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

# 浮点数域
class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

# 文本域
class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

# 对元类的理解我也不是很深刻，只能说点自己粗浅的看法，仅供参考
# 我们先捋一下继承关系吧，models.py中class User(Model)，这个继承很简单，大家都看的懂
# class Model(dict, metaclass=ModelMetaclass)这个继承前半部分也简单，就是继承dict
# 而后半部分metaclass=ModelMetaclass，这才是难点，我觉得这不是单纯的继承关系
# 如果说User类是一个产品，那么User继承的这些父类就是这个产品生产线上的一道工序，
# 而ModelMetaclass是一张加工图纸，配合最后一道工序来完成产品
# 我们知道object是所有类最终都会继承的类，所以我们可以把object比作产品原型
# object需要经过3道加工工序才能变成最后我们想要的User类这个成品，
# 这三道工序分别是dict，Model，User负责这三道工序的分别是d哥、M哥、U哥，
# 这三位哥们的工作很简单，就是从上一个哥们手里接过产品，加点东西然后交给下一个哥们
# 而Meta是个大神，大神怎么可能像上面三个哥们那样去流水线上干那么低级的活
# 所以他就画了一张叫ModelMetaclass的加工图纸，让拿到这张图纸的哥们照着这图纸加工就行了
# 那这图纸应该交给谁呢，Meta大神首先排除了d哥
# 因为d哥是厂里的老员工，虽然交代的任务他都能完成，但d哥缺乏创造力，思维僵化，看不懂Meta大神画的图纸
# 而M哥和U哥是刚毕业的大学生，可塑性非常好，图纸交给他们再合适不过了。那到底应该交给谁呢？
# Meta大神首先想到了U哥，因为这张图纸是配合最后一道工序来加工的，所以交给U哥应该最合适。
# 但这时候厂长找到Meta大神说要再增加两条产品线，一条用来生产Blog类，由B哥负责最后一道工序，
# 一条用来生产Comment类，由C哥负责最后一道工序
# 多了两条产品线，Meta大神的图纸需要重新画吗？当然不用，要不人家怎么叫大神呢。
# 只不过这样的话，Meta大神需要分别找U、B、C三位哥们把图纸给他们，这事儿太没效率了。
# 作为一个大神当然不能容忍这么没效率的做法，所以Meta大神想了一个好办法，那就是把图纸交给M哥，由
# M哥负责把图纸交给U、B、C三位哥们，但M哥也能看懂图纸，如果他傻乎乎的照着图纸加工一番，
# 那会把产品搞的一团糟所以Meta大神在图纸最前面加了一条说：“那个负责Model工序的哥们，
# 不要照我的图纸加工，直接把图纸交给下一个哥们就好了。”以上就是我对元类的理解，
# 我试过去掉Model类中的元类，把元类加到User类中同样可行，大家可以自己试下
# 元类定义如何构造一个雷。热火让定义来__metaclass__属性或制定了netaclass的都会通过元类
# 定义的构造方法，任何集成子Model的类都会自动通过Modelclass扫面映射关系并存储自身的类属性
class ModelMetaclass(type):
    # cls我不太清楚是什么，有些同学说相当于是self。
    # name是当前类的类名，bases是当前类继承的父类集合（元组），
    # attrs是当前类的属性（方法）集合，元类的作用就是操作当前类的属性集合然后生成一个新的属性集合
    # 那什么是当前类？拿前面做过的那个比喻来解释，当前类就是当前正在加工的这道工序。
    def __new__(cls, name, bases, attrs):
        #这就是前面说的，写在最前面防止Model类操作元类，大家可以试着在这儿print(name)
        # 排除Model类本身，因为model类本来就是用来被继承不存在与数据库表的映射
        if name=='Model':
            # 还有这儿print(name)
            return type.__new__(cls, name, bases, attrs)
        # 还有这儿print(name),这三个地方分别输出name这个变量，看一下输出结果后可能会更有感觉
        # 程序能执行到这儿，那就已经排除了当前类是Model这种情况，上面两句代码起的就是这个作用
        # 从这儿开始当前类只可能是User类、Blog类、Comment类，下面我们以User类为例来解释
        # tableName就是需要在数据库中对应的表名，如果User类中没有定义__table__属性，
        # 那默认表名就是类名，也就是User
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = dict()#创建一个空的dict是为了后面储存User类的属性
        fields = []#fields用来储存User类中除主键外的属性名
        primaryKey = None#主键默认为None，后面找到主键之后再赋值
        # attrs是User类的属性集合，是一个dict，
        # 需要通过items函数转换为[(k1,v1),(k2,v2)]这种形式，
        # 才能用for k, v in来循环
        # 遍历类的属性找出定义的域内的值，简历映设关系
        for k, v in attrs.items():
            if isinstance(v, Field):#检测v的类型是不是Field
                logging.info('  found mapping: %s ==> %s' % (k, v))
                #看到这儿大家一定很奇怪，attrs本来就是一个dict，把这个dict拆开来存入
                # 另一个dict是为什么？后面会解释的
                mappings[k] = v
                if v.primary_key:#如果该字段的主键值为True，那就找到主键了
                    if primaryKey:#在主键不为空的情况下又找到一个主键就会报错，因为主键有且仅有一个
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k#为主键赋值
                else:
                    fields.append(k)#不是主键的属性名储存到非主键字段名的list中
        if not primaryKey:#这就表示没有找到主键，也要报错，因为主键一定要有
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():#把User类中原有的属性全部删除
            attrs.pop(k)
        # fields中的值都是字符串，下面这个匿名函数的作用是在字符串两边加上``生成一个新的字符串
        # 为了后面生成sql语句做准备
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings #把mappings这个dict存入attrs这个dict中
        attrs['__table__'] = tableName#其实attrs本来可能就有__table__属性的，但前面attrs.pop(k)把attrs里面的东西全给删了，所以这里需要重新赋值
        attrs['__primary_key__'] = primaryKey #存入主键属性名
        attrs['__fields__'] = fields #存入除主键外的属性名
        #下面四句就是生成select、insert、update、delete四个sql语句，然后分别存入attrs
        #要理解下面四句代码，需要对sql语句格式有一定的了解，其实并不是很难
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)#一个全新的User类新鲜出炉了，慢慢享用吧

# 到这儿可以总结一下元类到底干了些什么，还是以User类为例
# 首先、元类找出User类在数据库中对应的表名，对User类的自有属性逐条进行分析，
# 找出主键和非主键，同时把这些属性全部存入mappings这个dict
# 然后、删除User类的全部属性，因为实际操作数据库的时候用不到这些属性
# 最后、把操作数据库需要用到的属性添加进去，这包括所有字段和字段类型的对应关系，
# 类对应的表名、主键名、非主键名，还有四句sql语句
# 这些属性才是操作数据库正真需要用到的属性，但仅仅只有这些属性还是不够，因为没有方法
# 而Model类就提供了操作数据库要用到的方法

class Model(dict, metaclass=ModelMetaclass):
    # 定义Model类的初始化方法
    def __init__(self, **kw):
        # 这里直接调用了Model的父类dict的初始化方法，把传入的关键字参数存入自身的dict中
        super(Model, self).__init__(**kw)

    # 没有这个方法，获取dict的值需要通过d[k]的方式，有这个方法就可以通过属性来获取值，也就是d.k
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    # 和上面一样，不过这个是用来设置dict的值，通过d.k=v的方式
    def __setattr__(self, key, value):
        self[key] = value

    # 上面两个方法是用来获取和设置**kw转换而来的dict的值，而下面的getattr是用来获取当前实例的属性值，不要搞混了
    def getValue(self, key):
        # 如果没有与key相对应的属性值则返回None
        return getattr(self, key, None)

    # 如果当前实例没有与key对应的属性值时，就需要调用下面的方法了
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            # 当前实例找不到想要的属性值时，就要到__mappings__属性中去找了，__mappings__属性对应的是一个dict，这个前面提过了
            field = self.__mappings__[key]
            if field.default is not None:  # 如果查询出来的字段具有default属性，那就检查default属性值是方法还是具体的值
                # 如果是方法就直接返回调用后的值，如果是具体的值那就返回这个值
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)#查到key对应的value后就设置为当前实例的属性，是为了方便下次查询？不是很确定
        return value

    @classmethod  # 这个装饰器是类方法的意思，这样就可以不创建实例直接调用类的方法
    # select操作的情况比较复杂，所以定义了三种方法
    @asyncio.coroutine
    def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '  # 通过条件来查询对象，一个对象对应数据库表中的一行
        sql = [cls.__select__]  # 有同学说cls就相当与是self，我感觉对象用self代表自己，类用cls代表自己，个人看法仅供参考
        if where:  # 如果有where条件就在sql语句中加入字符串'where'和变量where
            sql.append('where')
            sql.append(where)
        if args is None:  # 这个参数是在执行sql语句前嵌入到sql语句中的，如果为None则定义一个空的list
            args = []
        orderBy = kw.get('orderBy', None)  # 从**kw中取得orderBy的值，没有就默认为None
        if orderBy:  # 解释同where
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')  # sql中limit有两种用法
            if isinstance(limit, int):  # 如果limit为一个整数n，那就将查询结果的前n个结果返回
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                # 如果limit为一个两个值的tuple，则前一个值代表索引，后一个值代表从这个索引开始要取的结果数
                sql.append('?, ?')
                args.extend(limit)  # 用extend是为了把tuple的小括号去掉，因为args传参的时候不能包含tuple
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))  # 如果不是上面两种情况，那就一定出问题了
        rs = yield from select(' '.join(sql), args)  # sql语句和args都准备好了就交给select函数去执行
        return [cls(**r) for r in rs]  # 将查询到的结果一一返回，看不懂cls(**r)的用法，虽然能猜出这是个什么

    @classmethod
    @asyncio.coroutine
    def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '  # 根据where条件查询结果数，注意，这里查询的是数量
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]  # 这sql语句是直接重构的，不是调用属性，看不懂_num_是什么意思
        if where:
            sql.append('where')
            sql.append(where)
        rs = yield from  select(' '.join(sql), args, 1)
        if len(rs) == 0:  # 如果查询结果数为0则返回None
            return None
        return rs[0]['_num_']  # rs应该是个list，而这个list的第一项对应的应该是个dict，这个dict中的_num_属性值就是结果数，我猜应该是这样吧

    @classmethod
    @asyncio.coroutine
    def find(cls, pk):
        ' find object by primary key. '  # 根据主键查找是最简单的，而且结果只有一行，因为主键是独一无二的
        rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    # save、update、remove这三个方法需要管理员权限才能操作，所以不定义为类方法，需要创建实例之后才能调用
    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))  # 把实例的非关键字属性值全都查出来然后存入args这个list
        args.append(self.getValueOrDefault(self.__primary_key__))  # 把主键找出来加到args这个list的最后
        rows = yield from execute(self.__insert__, args)  # 执行sql语句后返回影响的结果行数
        # 一个实例只能插入一行数据，所以返回的影响行数一定为1,如果不为1那就肯定错了
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    # 下面两个的解释同上
    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)