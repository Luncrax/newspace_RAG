import asyncio
import os
import pickle
import shlex

from src.database.mysql_client import MySQLClient
from src.util.config_util import load_config


# ==============================================================================
# 常量定义
# ==============================================================================

# 保存所有 PDF ID 的文件
SCAN_IDS_FILE = "./data/download_set/scan_ids"

# 保存已下载 PDF ID 的文件
FINISHED_IDS_FILE = "./data/download_set/finished_download_set"

# PDF 下载目录
DOWNLOAD_DIR = "./data/download_pdfs"

# 远程服务器域名
REMOTE_HOST = "newspace.club"

# 数据库 path 中的前缀
PATH_PREFIX = "/newspace"


# ==============================================================================
# 初始化辅助函数
# ==============================================================================

def ensure_set_files():
    """
    确保以下资源存在：

    ./data/download_set/                  # 目录
    ./data/download_set/finished_download_set   # pickle 文件

    注意：
    - download_set 是目录
    - scan_ids 和 finished_download_set 是文件
    """
    os.makedirs("./data/download_set", exist_ok=True)

    if not os.path.exists(FINISHED_IDS_FILE):
        with open(FINISHED_IDS_FILE, "wb") as f:
            pickle.dump(set(), f)


# ==============================================================================
# 集合文件操作
# ==============================================================================

async def all_file_name_to_set(client: MySQLClient):
    """
    从数据库读取所有 PDF 的 file_id，并保存到:
        ./data/download_set/scan_ids
    """
    ensure_set_files()

    id_set = set()
    files_info = await client.get_all_pdf_info()

    for file_info in files_info:
        # file_info[0] 默认是 file_id
        id_set.add(file_info[0])

    with open(SCAN_IDS_FILE, "wb") as f:
        pickle.dump(id_set, f)

    print(f"[DEBUG] 已生成 scan_ids，共 {len(id_set)} 个文件")


def load_all_download_file():
    """
    读取所有 PDF ID 集合
    """
    ensure_set_files()

    if not os.path.exists(SCAN_IDS_FILE):
        raise FileNotFoundError(
            f"{SCAN_IDS_FILE} 不存在，请先执行 all_file_name_to_set(client)"
        )

    with open(SCAN_IDS_FILE, "rb") as f:
        return pickle.load(f)


def load_downloaded_file():
    """
    读取已下载文件 ID 集合
    """
    ensure_set_files()

    with open(FINISHED_IDS_FILE, "rb") as f:
        return pickle.load(f)


def add_download_set(file_id: str):
    """
    将 file_id 添加到已下载集合
    """
    ensure_set_files()

    finished_ids = load_downloaded_file()
    finished_ids.add(file_id)

    with open(FINISHED_IDS_FILE, "wb") as f:
        pickle.dump(finished_ids, f)


def get_undownload_set():
    """
    返回未下载文件的 ID 集合
    """
    all_ids = load_all_download_file()
    finished_ids = load_downloaded_file()
    return all_ids - finished_ids


# ==============================================================================
# 文件下载
# ==============================================================================

async def download_file(
    file_id: str,
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
    print(f"[DEBUG] file_id   = {file_id}")
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
            add_download_set(file_id)
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

    # 标记为已下载
    add_download_set(file_id)

    print("[DEBUG] 已加入 finished_download_set")
    print(f"[DEBUG] 下载完成: {local_path}")
    print("-" * 80)

    return local_path


# ==============================================================================
# 批量下载
# ==============================================================================

async def main():
    """
    下载所有尚未完成的 PDF 文件。
    单个文件失败时记录错误并继续。
    """

    # 加载配置
    config = load_config()

    # 初始化数据库客户端
    client = MySQLClient()
    await client.init(config)

    try:
        # 如果 scan_ids 不存在，自动生成
        if not os.path.exists(SCAN_IDS_FILE):
            print("[DEBUG] scan_ids 不存在，正在从数据库生成...")
            await all_file_name_to_set(client)

        # 获取未下载集合
        remaining = get_undownload_set()

        print(f"还有 {len(remaining)} 个文件未下载")

        if not remaining:
            print("所有文件均已下载完成")
            return

        success_count = 0
        failed_count = 0
        failed_files = []

        # 遍历下载
        for file_id in remaining:
            teamid = None
            file_name = "未知"
            path = None

            try:
                # file_info:
                # [0] -> teamid
                # [1] -> file_name
                # [2] -> path
                file_info = await client.get_pdf_info(file_id)

                if not file_info:
                    raise Exception("数据库中未找到文件信息")

                teamid = str(file_info[0])
                file_name = file_info[1]
                path = file_info[2]

                print(f"\n开始下载: file_id={file_id}, file_name={file_name}")

                local_path = await download_file(
                    file_id=str(file_id),
                    teamid=teamid,
                    file_name=file_name,
                    path=path,
                )

                print(f"下载成功: {local_path}")
                success_count += 1

            except Exception as e:
                failed_count += 1

                failed_files.append({
                    "file_id": file_id,
                    "teamid": teamid,
                    "file_name": file_name,
                    "path": path,
                    "error_type": type(e).__name__,
                    "error": str(e),
                })

                print("\n" + "=" * 100)
                print("下载失败（详细调试信息）")
                print("=" * 100)
                print(f"[DEBUG] file_id    : {file_id}")
                print(f"[DEBUG] teamid     : {teamid}")
                print(f"[DEBUG] file_name  : {file_name}")
                print(f"[DEBUG] db_path    : {path}")
                print(f"[DEBUG] error_type : {type(e).__name__}")
                print("[DEBUG] error_msg  :")
                print(str(e))
                print("=" * 100)
                print("继续下载下一个文件...")
                print("=" * 100)

                continue

        # 最终统计
        print("\n" + "=" * 100)
        print("下载任务完成")
        print("=" * 100)
        print(f"成功数量: {success_count}")
        print(f"失败数量: {failed_count}")

        if failed_files:
            print("\n失败文件列表:")
            for item in failed_files:
                print(
                    f"file_id={item['file_id']}, "
                    f"file_name={item['file_name']}, "
                    f"error={item['error']}"
                )

        remaining_after = get_undownload_set()
        print(f"\n当前剩余未下载数量: {len(remaining_after)}")
        print("=" * 100)

    finally:
        # 关闭数据库连接池
        client.pool.close()
        await client.pool.wait_closed()


# ==============================================================================
# 程序入口
# ==============================================================================

if __name__ == "__main__":
    asyncio.run(main())