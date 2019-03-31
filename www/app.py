import logging
logging.basicConfig(level=logging.INFO)
import os,json,time
from datetime import datetime
from aiohttp import web
import asyncio

def index(request):
    return web.Response(body=b'<h1>Awesome</h1>',content_type='text/html')

async def init(loop):
    app= web.Application(loop=loop)
    app.router.add_route('GET','/',index)
    srv =  await loop.create_server(app.make_handler(),'0.0.0.0',9000)
    logging.info('server started at 0.0.0.0:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()