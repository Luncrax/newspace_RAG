import pytest
from src.util.config_util import load_config
from src.database.redis_client import RedisClient
from src.database.mysql_client import MySQLClient
from src.database.redis_client import RedisClient

@pytest.mark.database
async def test_redis():
    config = load_config()
    redis = RedisClient(config)
    result = await redis.ping_redis()
    print(result)


@pytest.mark.database
async def test_mysql():
    config = load_config()
    mysql = MySQLClient()
    await mysql.init(config)
    result = await mysql.ping_mysql()
    print(result)


@pytest.mark.database
async def test_mysql_tags():
    config = load_config()
    mysql = MySQLClient()
    await mysql.init(config)
    result = await mysql.get_tags()
    print(result)



@pytest.mark.pdf_info
async def test_mysql_pdf():
    config = load_config()
    mysql = MySQLClient()
    await mysql.init(config)
    result = await mysql.get_all_pdf_info()
    print(result)
