from redis import asyncio as aio_redis
from src.model.config_model import Config


class RedisClient:
    """redis异步客户端"""
    client: aio_redis.Redis
    download_key: str
    ocr_key: str
    rag_key: str

    def __init__(self, config: Config) -> None:
        self.client = aio_redis.Redis(
            host=config.database.redis.url,
            port=config.database.redis.port,
            password=config.database.redis.password,
            db=config.database.redis.db,
            decode_responses=True
        )
        self.download_key = config.database.redis.stream_download
        self.ocr_key = config.database.redis.stream_ocr
        self.rag_key = config.database.redis.stream_rag


    async def ping_redis(self):
        result = await self.client.ping() # type: ignore
        print(result)

    async def append_stream(self, stream_key_name: str, data: dict):
        """向stream中添加数据"""
        await self.client.xadd(stream_key_name, data)


    async def read_stream(self, stream_key_name: str):
        return await self.client.xread(streams={stream_key_name: "0"}, block=0, count=1)
    
    async def del_stream(self, stream_key_name: str, stream_id: str):
        pass