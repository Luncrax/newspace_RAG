import pytest
from src.util.config_util import load_config
from src.database.mysql_client import MySQLClient
from src.util.download_file import download_all_files, all_file_name_to_set, add_download_set,get_undownload_set
import pickle

@pytest.mark.test_set
async def test_set():
    config = load_config()
    mysql = MySQLClient()
    await mysql.init(config)
    result = await mysql.get_all_pdf_info()
    print(result)
    await all_file_name_to_set(mysql)
    with open("./data/download_set/scan_ids", "rb") as f:
        load_set = pickle.load(f)

    print(load_set)

@pytest.mark.test_download()
async def test_download():
    config = load_config()
    mysql = MySQLClient()
    await mysql.init(config)
    await download_all_files(mysql)

@pytest.mark.cha()
async def cha():
    print(await get_undownload_set())