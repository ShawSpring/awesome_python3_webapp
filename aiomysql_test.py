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

loop.run_until_complete(test_example3())
