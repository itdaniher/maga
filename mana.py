from maga import Maga
from mala import get_metadata
import sys

import asyncio

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except:
    pass

import time

import handlebars

f = open(str(int(time.time()))+".ih.log", 'w')
ih2bytes = lambda x: bytes(bytearray.fromhex(x))

class Crawler(Maga):
    def __init__(self, loop=None, active_tcp_limit = 1000, max_per_session = 2500):
        super().__init__(loop)
        self.seen_ct = 0
        self.active = asyncio.Semaphore(active_tcp_limit)
        self.threshold = active_tcp_limit
        self.max = max_per_session
        self.connection = asyncio.get_event_loop().run_until_complete(handlebars.init_redis('mana.sock'))

    async def handler(self, infohash, addr, peer_addr = None):
        exists = await self.connection.exists(ih2bytes(infohash))
        if self.running and (self.seen_ct < self.max) and not exists:
            await self.connection.set(ih2bytes(infohash), b'', pexpire=int(6e8)) #expires in 1wk
            self.seen_ct += 1
            if peer_addr is None:
                peer_addr = addr
            async with self.active:
                metainfo = await get_metadata(
                    infohash, peer_addr[0], peer_addr[1], loop=self.loop
                )
            await self.log(metainfo, infohash)
        if (self.seen_ct >= self.max):
            self.stop()

    async def log(self, metainfo, infohash):
        if metainfo not in [False, None]:
            try:
                out = infohash+' '+ metainfo[b'name'].decode('utf-8').replace('\n', '\\n')+'\n'
                sys.stdout.write(out)
                f.write(out)
                f.flush()
            except UnicodeDecodeError:
                print(infohash+'    (not rendered)')


port = int(sys.argv[1])

handlebars.start_redis_server('mana.sock')
crawler = Crawler()
crawler.run(port, False)

if len(sys.argv) > 2 and sys.argv[2] == "--forever":
    while True:
        new_crawler = Crawler()
        new_crawler.seen = crawler.seen
        del crawler
        crawler = new_crawler
        time.sleep(5)
        new_crawler.run(port, False)
        print('>>> crawler round done', crawler.loop, new_crawler.loop)
