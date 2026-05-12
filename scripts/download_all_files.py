from src.util.download_file import *
from src.service.ocr_pdf_to_text import pdf_to_text
import asyncio

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
    await all_file_name_to_set(client)
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


if __name__ == '__main__':
    asyncio.run(main())