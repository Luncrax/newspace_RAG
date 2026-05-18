import pickle
from src.database.mysql_client import MySQLClient
from src.database.mongodb_client import MongodbClient
from src.util.config_util import load_config
from src.service.use_deepseek import *
from pathlib import Path
import asyncio
import os

from paddleocr import PaddleOCR
from src.service.ocr_pdf_to_text import pdf_to_text
import shlex

def dump_fav_pkl(input_set: set):
    """保存 set 到 pkl 文件"""
    Path("./data/fav_data/pkl_data/").mkdir(parents=True, exist_ok=True)
    with open("./data/fav_data/pkl_data/fav_processed_file", "wb") as f:
        pickle.dump(input_set, f)
def load_processed_pkl() -> set:
    """从 pkl 文件加载 set"""
    file_path = Path("./data/fav_data/pkl_data/fav_processed_file")
    if not file_path.exists():
        return set()
    with open(file_path, "rb") as f:
        return pickle.load(f)

async def process_all_fav(mysql: MySQLClient, mongo: MongodbClient):
    #1. 读取pkl文件
    processed_file_id = load_processed_pkl()
    #2. 数据库查查询
    all_file_id = set()
    pdfs_info = await mysql.get_all_fav_pdf_info()
    for pdf_info in pdfs_info:
        all_file_id.add(pdf_info[0])
    need_process_id = all_file_id - processed_file_id
    need_process_info = set()
    for file_id in need_process_id:
        need_process_info.add(await mysql.get_fav_pdf_info(file_id))
    for file_info in need_process_info:
        file_path = file_info[2]
        team_id = file_info[0]
        file_name = file_info[1]
        file_id = file_info[3]
        #3. 下载pdf
        #4. ocr
        text = ocr_fav(file_name, await download_file(team_id, file_name, file_path))
        #5. 结构化并插入
        await process_single_file_fav(team_id, text, mongo)
        #6: 写入pkl文件
        processed_file_id.add(file_id)
        dump_fav_pkl(processed_file_id)
    #7. 完成


async def process_single_file_fav(team_id, text ,mongo_client):
    """
    处理单个文件
    """
    try:
        # 调用 LLM 处理
        result = structure_document(
            text,  # 传入文件内容
            MONGODB_PROMPT,
        )
        # 添加 team_id 到结果中
        result["team_id"] = team_id
    
        # 插入到 MongoDB
        await mongo_client.insert_json_string("newspace_documents", "newspace_fav", json.dumps(result))
        
        print(f"成功处理: {team_id}")
        return True
        
    except Exception as e:
        print(f"处理文件 {team_id} 时出错: {e}")
        return False


def ocr_fav(file_name:str, file_path: str) -> str:
    OUTPUT_DIR = Path("./data/fav_data/ocred_pdfs")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        print(f"\n开始 OCR: {file_name}")
        # OCR
        return pdf_to_text(str(file_path))
    except Exception as e:
        print(f"OCR 失败: {file_name}")
        print(type(e).__name__, e)
        raise


# PDF 下载目录
DOWNLOAD_DIR = "./data/fav_data/download_pdfs"

# 远程服务器域名
REMOTE_HOST = "newspace.club"

# 数据库 path 中的前缀
PATH_PREFIX = "/newspace"
async def download_file(
    teamid: str,
    file_name: str,
    path: str,
):
    """
    下载单个 PDF 文件

    参数:
        file_id   : 数据库中的文件 ID
        teamid    : 团队 ID
        file_name : 文件显示名称
        path      : 数据库中的完整文件路径

    返回:
        本地文件路径
    """

    print("\n" + "-" * 80)
    print("[DEBUG] 开始 download_file")
    print(f"[DEBUG] teamid    = {teamid}")
    print(f"[DEBUG] file_name = {file_name}")
    print(f"[DEBUG] db path   = {path}")

    # 去掉 /newspace 前缀
    if path.startswith("/newspace"):
    # 去掉 /newspace 前缀
        remote_path = path[len("/newspace"):]

    elif path.startswith("/apps/data/team"):
        # 已经是完整路径
        remote_path = path

    elif path.startswith("/upload/"):
        # 补全为真实路径
        remote_path = os.path.join(
            "/apps/data/team",
            path.lstrip("/")
        )
    elif path.startswith("/profile/upload/"):
        # profile 路径实际也存放在 upload 目录中
        # 例如：
        # /profile/upload/2026/05/07/a.pdf
        # -> /apps/data/team/upload/2026/05/07/a.pdf
        remote_path = os.path.join(
            "/apps/data/team",
            path[len("/profile/"):].lstrip("/")
        )
    else:
        # 兜底：直接拼到 /apps/data/team 下
        remote_path = os.path.join(
            "/apps/data/team",
            path.lstrip("/")
        )
    print(f"[DEBUG] normalized remote_path = {remote_path}")
    # 创建本地下载目录
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    # 使用 path 中真实文件名，避免 file_name 与实际文件名不一致
    remote_real_name = os.path.basename(remote_path)
    # 本地文件名：teamid_真实文件名
    local_file_name = f"{teamid}_{remote_real_name}"
    local_path = os.path.join(DOWNLOAD_DIR, local_file_name)
    print(f"[DEBUG] local_path = {local_path}")
    # 文件已存在且大小大于 0，视为下载完成
    if os.path.exists(local_path):
        size = os.path.getsize(local_path)
        print(f"[DEBUG] 本地文件已存在, size = {size}")
        if size > 0:
            print("[DEBUG] 文件已存在，跳过下载")
            return local_path
    # 构造 scp 命令（安全处理特殊字符）
    remote_spec = f"root@{REMOTE_HOST}:{shlex.quote(remote_path)}"
    local_spec = shlex.quote(local_path)
    cmd = f"scp {remote_spec} {local_spec}"
    print(f"[DEBUG] scp cmd = {cmd}")
    # 异步执行 scp
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    stdout_text = stdout.decode(errors="ignore")
    stderr_text = stderr.decode(errors="ignore")
    print(f"[DEBUG] returncode = {process.returncode}")
    if stdout_text.strip():
        print(f"[DEBUG] stdout:\n{stdout_text}")
    if stderr_text.strip():
        print(f"[DEBUG] stderr:\n{stderr_text}")
    # 检查 scp 是否成功
    if process.returncode != 0:
        raise Exception(
            "文件下载失败:\n"
            f"remote_path={remote_path}\n"
            f"error={stderr_text.strip()}"
        )

    # 校验文件是否存在
    if not os.path.exists(local_path):
        raise Exception(f"文件不存在: {local_path}")

    # 校验文件大小
    file_size = os.path.getsize(local_path)
    print(f"[DEBUG] downloaded size = {file_size}")

    if file_size == 0:
        raise Exception(f"文件下载不完整: {local_path}")


    print("[DEBUG] 已加入 finished_download_set")
    print(f"[DEBUG] 下载完成: {local_path}")
    print("-" * 80)

    return local_path

async def main() -> None:
    config = load_config()
    mysql = MySQLClient()
    await mysql.init(config)
    mongo = MongodbClient(config)
    await process_all_fav(mysql, mongo)


if __name__ == '__main__':
    asyncio.run(main())