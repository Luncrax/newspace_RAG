from datetime import datetime
from src.database.mysql_client import MySQLClient
import pickle
import os
import os
import asyncio

from datetime import datetime


async def download_file(file_id: str, teamid: str, file_name: str, path: str):

    path = path[9:]
    # 2. 拼接服务器目录
    remote_dir = os.path.join(
    "/apps/data/team",
    path.lstrip("/")
)
    # 3. 拼接远程文件完整路径
    remote_path = f"{remote_dir}"

    # 4. 本地保存目录
    local_dir = f"./data/download_pdfs"

    os.makedirs(local_dir, exist_ok=True)

    # 5. 本地文件路径
    local_path = os.path.join(local_dir, f"{teamid}_{file_name}")

    # 6. 如果文件已存在，直接返回
    if os.path.exists(local_path):

        # 防止下载到一半的空文件
        if os.path.getsize(local_path) > 0:
            return local_path

    # 7. scp命令
    cmd = (
        f"scp "
        f"root@newspace.club:'{remote_path}' "
        f"'{local_path}'" 
    )

    # 8. 异步执行scp
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    # 9. 检查scp是否成功
    if process.returncode != 0:

        error_msg = stderr.decode()

        raise Exception(
            f"文件下载失败:\n"
            f"remote_path={remote_path}\n"
            f"error={error_msg}"
        )

    # 10. 校验文件是否存在
    if not os.path.exists(local_path):

        raise Exception(
            f"文件不存在: {local_path}"
        )

    # 11. 校验文件大小
    if os.path.getsize(local_path) == 0:

        raise Exception(
            f"文件下载不完整: {local_path}"
        )
    await add_download_set(file_id)
    return local_path



async def all_file_name_to_set(client: MySQLClient):
    """将数据库中目前所以的pdf id 存入set,并存储至./data/download_set"""
    id_set = set()
    files_info = await client.get_all_pdf_info()
    for file_info in files_info:
        id_set.add(file_info[0])
    with open("./data/download_set/scan_ids", "wb") as f:
        pickle.dump(id_set, f)

async def load_all_download_file():
    with open("./data/download_set/scan_ids", "rb") as f:
        return pickle.load(f)

async def load_downloaded_file():
    with open("./data/download_set/finished_download_set", "rb") as f:
        return pickle.load(f)



async def add_download_set(id: str):
    with open("./data/download_set/finished_download_set", "rb") as f:
        load_set = pickle.load(f)
    load_set.add(id)
    with open("./data/download_set/finished_download_set", "wb") as f:
        pickle.dump(load_set, f)

async def get_undownload_set():
    all = await load_all_download_file()
    finished = await load_downloaded_file()
    need = all - finished
    return need

async def download_all_files(client: MySQLClient):
    for id in await get_undownload_set():
        file_info = await client.get_pdf_info(id)
        await download_file(id, file_info[0], file_info[1], file_info[2])
