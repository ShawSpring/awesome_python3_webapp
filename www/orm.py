__author__ = 'xcl'

import aiomysql, asyncio
import logging
logging.basicConfig(level=logging.INFO)


def log(sql, args=()):
    logging.info('SQL:%s' % sql)


async def create_pool(pool, **kw):
    logging.info('create database connection pool ...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['root'],
        password=kw['mysql608213'],
        db=kw['test'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop)


async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:  #with (await __pool) as conn:
        async with conn.cursor(
                aiomysql.DictCursor
        ) as cur:  # cur = await conn.cursor(aiomysql.DictCursor)
            await cur.execute(sql.replace('?','%s'), args or ())
            #SQL语句的占位符是?，而MySQL的占位符是%s
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
                # await cur.close() 使用了上下文管理器就不需要手动close() 了
        logging.info('rows returned: %s' % len(rs))
        return rs


#delete update insert 三种语句模式一样,写到一个函数里,
async def execute(sql, args, autocommit=True):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                affected = await cur.execute(sql.replace('?','%s'), args or ())
            logging.info('effected rows: %s' % affected)
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected

class Field(object):
    def __init__(self,name,column_type,primarykey,default):
        self.name=name
        self.column_type=column_type
        self.primarykey=primarykey #标志  是否为主键
        self.default=default
    
    def __str__(self):
        return "<%s,%s:%s>"%(self.__class__.__name__,self.name,self.column_type)

class StringField(Field):
    def __init__(self, name, column_type, primarykey=False, default=None,ddl='varchar(50)'):
        return super().__init__(name, ddl, primarykey, default)



class ModelMetaclass(type):
    def __new__(cls,name,bases,attrs):
        if name=="Model":
            return type.__new__(cls,name,bases,attrs)
        mappinngs={}
        primarykey = None
        fields = []  #非主键的 字段集合
        tablename = attrs.get('__tablename__') or name
        for k,v in attrs.items():
            if isinstance(v,Field):
                mappinngs[k] = v
                if v.primarykey: #这个field设置了 为主键
                    if primarykey:
                        raise ValueError('Duplicated primary key')
                    primarykey = k
                else:
                    fields.append(k)
        if not primarykey:  #遍历了也没有主键 错误
            raise ValueError('Primary key not found')
        for k in mappinngs.keys():
            attrs.pop(k)
        attrs['__mappings__'] = mappinngs
        attrs['__tablename__'] = tablename
        attrs['__fields__'] = fields
        attrs['__primarykey__'] = primarykey
        # 字符串里的占位符是%S  为了与mysql里的占位符区分,先把mysql里的参数占位符用?
        attrs['__select__'] = 'select %s,%s from %s'%(primarykey,','.join(fields),tablename)
        attrs['__insert__'] = "insert into %s(%s,%s) values(%s)"\
        %(tablename,','.join(fields),primarykey,','.join(['?' for x in range(len(fields)+1)]))
        #update set id=?,name=?,email=? where id =?
        attrs['__update__'] = "update %s set %s where %s =?"\
        %(tablename,",".join(list(map(lambda f:"%s=?"%mappinngs.get(f).name or f,fields))),primarykey)
        #delete from user where %s =?
        attrs['__delete__'] = "delete from %s where %s=?"%(tablename,primarykey)
        return type.__new__(cls,name,bases,attrs)


class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        return super().__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' has no attribute %s"%key)

    def __setattr__(self, name, value):
        self[name] = value

    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value = getattr(self,key,None)
        if not value:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug("get default value for %s:%s"%(key,str(value)))  #debug是最低的级别 CRITICAL > ERROR > WARNING > INFO > DEBUG

                setattr(self,key,value)
        return value
         