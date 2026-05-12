import pytest
from src.util.config_util import load_config
from src.database.mongodb_client import MongodbClient

@pytest.mark.test_mongo
async def test_mongo():
    client = MongodbClient(load_config())
    await client.ping()