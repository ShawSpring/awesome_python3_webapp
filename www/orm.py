
__author__ = 'xcl'

import aiomysql, asyncio
import logging
logging.basicConfig(level=logging.INFO)

def log(sql, args=()):
    logging.info('SQL:%s' % sql)


async def create_pool(loop=None, **kw):
    logging.info('create database connection pool ...')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'), #可以传参到kw, 也可以默认值
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop)
        
async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    async with __pool.acquire() as conn:  #with (await __pool) as conn:
        async with conn.cursor(
                aiomysql.DictCursor # 返回的结果是dict类型[{'__num__': 3}] 默认是tuple类型 ((3,),)
        ) as cur:  
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
        self.primarykey=primarykey #标志   是否为主键
        self.default=default
    
    def __str__(self):
        return "<%s,%s:%s>"%(self.__class__.__name__,self.name,self.column_type)

class StringField(Field):
    def __init__(self, name=None, primarykey=False, default=None,ddl='varchar(50)'):
        return super().__init__(name, ddl, primarykey, default)

class IntegerField(Field):
    def __init__(self, name=None, primarykey=False, default=None,ddl='int'):
        return super().__init__(name, ddl, primarykey, default)

class FloatField(Field):
    def __init__(self, name=None, primarykey=False, default=0.0):
        return super().__init__(name, 'real', primarykey, default)

class BooleanField(Field):
    def __init__(self, name=None, default=False):
        return super().__init__(name, 'boolean', False, default)

class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetaclass(type):
    def __new__(cls,name,bases,attrs):
        if name == "Model":
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
        %(tablename,",".join(list(map(lambda f:"%s=?"%(mappinngs.get(f).name or f),fields))),primarykey)

        #delete from user where %s =?
        attrs['__delete__'] = "delete from %s where %s=?"%(tablename,primarykey)
        return type.__new__(cls,name,bases,attrs)

'''
Model xxx
'''
class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super().__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' has no attribute %s"%key)

    def __setattr__(self, name, value):
        self[name] = value

    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):#在sql语句中需要保证 字段没有赋值则获取默认值
        value = getattr(self,key,None)
        if not value:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug("get default value for %s:%s"%(key,str(value)))  #debug是最低的级别 CRITICAL > ERROR > WARNING > INFO > DEBUG
                setattr(self,key,value)
        return value
         
    @classmethod
    async def find(cls,pk):
    #' find object by primary key '
        rs = await select('%s where %s = ?'%(cls.__select__,cls.__primarykey__),pk,1)
        if len(rs) ==0:
            return None
        return cls(**rs[0])

    @classmethod
    async def findNumber(cls,selectField,where=None,args=None):
        #find number by selelct and where
        sqlstr = ['select %s __num__ from %s'%(selectField,cls.__tablename__)]
        if where:
            sqlstr.append('where')
            sqlstr.append(where)
        r = await select(' '.join(sqlstr),args,1) #返回记录集
        if len(r)==0: #返回记录条数为0
            return None
        return r[0]['__num__']
        #return r[0][0] #返回第一条记录的第一个值
    

    @classmethod
    async def findAll(cls,where=None,args=None,**kw):
        sqlstr = [cls.__select__] #基本语句
        if where:
            sqlstr.append('where')
            sqlstr.append(where)
        if not args:
            args = []

        orderby = kw.get("orderby",None) #命名参数名,不加空格
        if orderby:
            sqlstr.append('order by')
            sqlstr.append(orderby)

        limit = kw.get('limit',None)
        if limit:
            sqlstr.append('limit')
            if isinstance(limit,int):
                sqlstr.append(limit)
            elif isinstance(limit,tuple) and len(limit)==2:
                sqlstr.append("%s,%s"%(limit[0],limit[1]))
            else:
                raise ValueError('Invalid limit value: %s'%str(limit))
        rs = await select(' '.join(sqlstr),args)
        return [cls(**r) for r in rs]
    
    async def save(self):
        args = list(map(self.getValueOrDefault,self.__fields__))
        args.append(self.getValueOrDefault(self.__primarykey__))#获取主键值 没有则拿Field中规定的默认值
        r = await execute(self.__insert__,args)
        if r!=1: #受影响的行数不是1
            logging.warn('failed to insert record: affected rows:%s'%r)
        return r

    async def update(self):
        args = list(map(self.getValueOrDefault,self.__fields__))
        args.append(self.getValueOrDefault(self.__primarykey__))#获取主键值 没有则拿Field中规定的默认值
        r = await execute(self.__update__,args)
        if r!=1: #受影响的行数不是1
            logging.warn('failed to update record by primarykey: %s affected rows:%s'%(args[-1],r))
        return r

    async def remove(self):
        args = [self.getValueOrDefault(self.__primarykey__)]
        r = await execute(self.__delete__,args) # cur.execute(sql,args) args必须是tuple or list
        if r!=1: #受影响的行数不是1
            logging.warn('failed to delete record by primarykey: %s affected rows:%s'%(args[-1],r))
        return r
        

        


            

