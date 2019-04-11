import asyncio,aiomysql

loop = asyncio.get_event_loop()

db =dict(host='127.0.0.1', 
    port=3306,
    user='xcl', 
    password='password', 
    db='awesome',
    loop=loop)

@asyncio.coroutine
def test_example1():
    conn = yield from aiomysql.connect(**db)

    cur = yield from conn.cursor()
    yield from cur.execute("SELECT * from users")
    print(cur.description)
    r = yield from cur.fetchall()
    print(r)
    yield from cur.close()
    conn.close()

async def test_example2():
    async with aiomysql.connect(**db) as conn:
        async with conn.cursor() as cur:
            r = await cur.execute("select * from users where name = %s",('xiao',))
            #print(cur.description )
            print(r)
            results = await cur.fetchall()
            print(results)

# pool
async def test_example3():
    pool = await aiomysql.create_pool(**db)
    # async with pool as conn:  # 这里不是打开pool对象, 而是等待pool yield出一个conn
    # async with 打开的仍是pool类型的东西, 会报错 'Pool' object has no attribute 'cursor'
    with await pool as conn:
        async with conn.cursor() as cur:
            r = await cur.execute("select * from users where name = %s",('xiao',))
            print(r)
            results = await cur.fetchall()
            print(results)

async def test_example4():
    pool = await aiomysql.create_pool(**db)
    # async with pool as conn:  # 这里不是打开pool对象, 而是等待pool yield出一个conn
    # async with 打开的仍是pool类型的东西, 会报错 'Pool' object has no attribute 'cursor'
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sqlstr = 'select  %s  __num__  from %s'%('count(id)','blogs')
            r = await cur.execute(sqlstr,())
            print(r)
            #print(r[0]['__num__'])
            # results = await cur.fetchall()
            # print(results)
            
            results = await cur.fetchmany(2)
            print(str(results))

loop.run_until_complete(test_example4())

l = [{'__num__': 2}]
print(l[0]['__num__'])