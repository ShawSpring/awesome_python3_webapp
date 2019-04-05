
from aiohttp import web
import os,inspect,logging,logging
import functools
from urllib import parse

from apis import APIError

#这里面的fn func 皆是指 handlers.py 里面的 url处理函数


#把函数映射成url处理函数  给函数加上 method  和 url属性
def get(path):
    def decoration(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__= 'GET'
        wrapper.__url__ = path
        return wrapper
    return decoration

def pose(path):
    def decoration(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__='POST'
        wrapper.__url__=path
        return wrapper
    return decoration

# 5个分析函数参数 的函数

# 必填的命名关键字参数 
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items(): #inspect.Parameter.empty指连默认值都没有,必须要填写的参数
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

'''
从fn中获取它的命名关键字参数
return: tuple(关键字参数名)
'''
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

#对 类似如下这种 url 处理函数 进行封装 
'''
本来 aiohttp最简单的处理函数是这样 
async def hello(request):
    parse(request) # 1. 分析需要接收的参数, 2. 从request中获取需要的参数,调用url函数
    text = '<h1>hello, %s!</h1>' % request.match_info['name']
    return web.Response(body=text.encode('utf-8')) #将结果转换成response对象 并返回
'''

class RequestHandler(object):

    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn) #是否有'request'
        self._has_var_kw_arg = has_var_kw_arg(fn) #是否有可变参数
        self._has_named_kw_args = has_named_kw_args(fn) #是否有命名关键字参数
        self._named_kw_args = get_named_kw_args(fn) # 获取命名关键字参数 
        self._required_kw_args = get_required_kw_args(fn) # 必填的命名关键字参数 

    async def __call__(self, request):
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type.')
                ct = request.content_type.lower()
                if ct.startswith('application/json'): #json型 
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'): #表单型
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # remove all unamed kw:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

#app 路由添加 静态文件 处理
def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static') #当前目录/static
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

#注册url处理函数
def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

#调用上面的add_route(),自动把handlers模块的所有符合条件的函数注册了: 
def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:] # 形如import XXX.handles  则只取handls
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    #对导入的mod 进行 扫描  
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)  #必须用 get/post 装饰过,有了method route的合法url处理函数
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)