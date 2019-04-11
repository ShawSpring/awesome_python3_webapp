import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from aiohttp import web

from coroweb import get, post
from apis import APIValueError, APIResourceNotFoundError,APIError,APIPermissionError

from models import User, Comment, Blog, next_id
from config import configs

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

@asyncio.coroutine
def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = yield from User.find(uid) #每次cookie验证都需要用到数据库
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

@get('/')
def index(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
    ]
    # ## 增加显示目前用户名的功能
    # request.__user__ = None
    # cookie_str = request.cookies.get(COOKIE_NAME)
    # if cookie_str:
    #     user = yield from cookie2user(cookie_str)
    #     if user:
    #         request.__user__ = user

    user = getattr(request,'__user__',None)
    return {
        '__template__': 'blogs.html',
        'blogs': blogs,
        '__user__':user
    }

@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

@post('/api/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # check passwd:
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid password.')
    # authenticate ok, set cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True) #max_age=0 就会被浏览器删除该cookie
    logging.info('user signed out.')
    return r

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

@post('/api/users')
async def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')  #user可以直接dumps 继承自dict
    return r


@get('/manage/blogs/create')
def manange_blogs_create():
    return {
        '__template__':'manage_blog_edit.html', #可以作为 创建 也可以 作为修改编辑
        'id':'',
        'action':'/api/blogs' #调用创建blog的action 
    }

# @get('/blog/{id}')
# def get_blog(id):
#     blog = yield from Blog.find(id)
#     comments = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
#     for c in comments:
#         c.html_content = text2html(c.content)
#     blog.html_content = markdown2.markdown(blog.content)
#     return {
#         '__template__': 'blog.html',
#         'blog': blog,
#         'comments': comments
#     }

@get('/api/blogs/{id}')
async def api_get_blog(*,id):
    blog = await Blog.find(id)
    return blog


@post('/api/blogs') #关于用户的信息已经在 auth_factory 里通过验证cookie的到了
async def api_create_blog(request,*,name,summary,content): #只需要关注blog本身的信息
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name','blog name cannnot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary','blog summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content','blog content cannot be empty')
    blog = Blog(user_id=request.__user__.id,user_name=request.__user__.name,user_image=request.__user__.image,
    name=name.strip(),summary = summary.strip(),content =content.strip())
    await blog.save()
    return blog


@get('/test')
def test():
    return {
        '__template__':'test.html'
    }

@post('/api/querryuser')
async def api_querry_user(*,email):
    if not email or not email.strip():
        raise APIValueError('email')  #会返回一个dict,被 response 里的函数json.dumps()
    if not _RE_EMAIL.match(email):
        raise APIValueError('email')
    users = await User.findAll(where='email = ?',args = (email,))
    if len(users) == 0:
        raise APIError('Invalid email',email,'email not exist')
    return json.dumps(users[0],ensure_ascii= False).encode('utf-8')
