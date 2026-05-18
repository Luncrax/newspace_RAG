from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.service.download_all_files import main as download_main
from src.service.ocr_all_files import main as ocr_main
from src.service.txt_to_document import main as mongo_main
import asyncio

HOUR1 = 8
MINUTE1 = 0
HOUR2 = 20
MINUTE2 = 0

async def test_info():
    print("执行了一次异步任务")

async def mix_functions():
    await test_info()
    await download_main()
    ocr_main()
    await mongo_main()

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(mix_functions, 'cron', hour=HOUR1, minute=MINUTE1)
    scheduler.add_job(mix_functions, 'cron', hour=HOUR2, minute=MINUTE2)
    scheduler.start()
    print("调度器已启动，等待任务执行...")
    
    # 保持运行
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()  # 永久等待
    except KeyboardInterrupt:
        print("\n收到退出信号，正在关闭...")
        scheduler.shutdown()

asyncio.run(main())