from src.util.config_util import load_config
from src.database.mongodb_client import MongodbClient
from src.service.use_deepseek import *
from pathlib import Path
import asyncio
import pickle
import os


def get_unprocessed_files():
    """
    获取未处理的文件列表
    返回: list of tuple (team_id, file_path)
    """
    # 1. 遍历 data/ocr_finished_team_pdf 目录，获取所有 team_id.txt 文件
    ocr_dir = Path("data/ocr_finished_team_pdf")
    if not ocr_dir.exists():
        print(f"警告: 目录 {ocr_dir} 不存在")
        return []
    
    # 创建文件名集合（不含 .txt 后缀）
    all_files_set = set()
    file_path_map = {}  # 存储 team_id 到文件路径的映射
    
    for txt_file in ocr_dir.glob("*.txt"):
        team_id = txt_file.stem  # 获取不带扩展名的文件名
        all_files_set.add(team_id)
        file_path_map[team_id] = txt_file
    
    print(f"发现 {len(all_files_set)} 个待处理的文件")
    
    # 2. 读取 data/llm_finished.pkl 中已完成的文件集合
    finished_set = set()
    pkl_path = Path("data/llm_finished.pkl")
    
    if pkl_path.exists():
        try:
            with open(pkl_path, "rb") as f:
                finished_set = pickle.load(f)
            print(f"已处理文件数: {len(finished_set)}")
        except Exception as e:
            print(f"读取 llm_finished.pkl 失败: {e}")
            # 如果读取失败，创建新的集合
            finished_set = set()
    else:
        print("llm_finished.pkl 不存在，将创建新文件")
        # 确保 data 目录存在
        pkl_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 3. 计算未处理的文件
    unprocessed_set = all_files_set - finished_set
    unprocessed_files = [(team_id, file_path_map[team_id]) for team_id in unprocessed_set]
    
    print(f"待处理文件数: {len(unprocessed_files)}")
    
    return unprocessed_files

def save_finished_file(team_id):
    """
    将已处理的 team_id 保存到 llm_finished.pkl
    """
    pkl_path = Path("data/llm_finished.pkl")
    
    # 读取现有的完成集合
    finished_set = set()
    if pkl_path.exists():
        try:
            with open(pkl_path, "rb") as f:
                finished_set = pickle.load(f)
        except Exception as e:
            print(f"读取 llm_finished.pkl 失败: {e}")
    
    # 添加新的 team_id
    finished_set.add(team_id)
    
    # 保存回文件
    try:
        with open(pkl_path, "wb") as f:
            pickle.dump(finished_set, f)
        print(f"已记录完成文件: {team_id}")
    except Exception as e:
        print(f"保存 llm_finished.pkl 失败: {e}")

async def process_single_file(team_id, file_path, config, mongo_client):
    """
    处理单个文件
    """
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            print(f"警告: {team_id} 文件内容为空")
            return False
        
        # 调用 LLM 处理
        result = structure_document(
            content,  # 传入文件内容
            MONGODB_PROMPT,
        )
        
        # 添加 team_id 到结果中
        result["team_id"] = team_id
        
        # 插入到 MongoDB
        await mongo_client.insert_json_string("newspace_documents", "newspace", json.dumps(result))
        
        # 保存完成记录
        save_finished_file(team_id)
        
        print(f"成功处理: {team_id}")
        return True
        
    except Exception as e:
        print(f"处理文件 {team_id} 时出错: {e}")
        return False

async def process_single_file_fav(team_id, file_path, config, mongo_client):
    """
    处理单个文件
    """
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            print(f"警告: {team_id} 文件内容为空")
            return False
        
        # 调用 LLM 处理
        result = structure_document(
            content,  # 传入文件内容
            MONGODB_PROMPT,
        )
        
        # 添加 team_id 到结果中
        result["team_id"] = team_id
        
        # 插入到 MongoDB
        await mongo_client.insert_json_string("newspace_documents", "newspace_fav", json.dumps(result))
        
        # 保存完成记录
        save_finished_file(team_id)
        
        print(f"成功处理: {team_id}")
        return True
        
    except Exception as e:
        print(f"处理文件 {team_id} 时出错: {e}")
        return False

async def main() -> None:
    # 加载配置
    config = load_config()
    
    # 获取未处理的文件列表
    unprocessed_files = get_unprocessed_files()
    
    if not unprocessed_files:
        print("没有需要处理的文件")
        return
    
    print(f"开始处理 {len(unprocessed_files)} 个文件...")
    
    # 初始化 MongoDB 客户端
    mongo_client = MongodbClient(config)
    
    # 处理每个文件
    success_count = 0
    fail_count = 0
    
    for team_id, file_path in unprocessed_files:
        print(f"\n处理: {team_id}")
        success = await process_single_file(team_id, file_path, config, mongo_client)
        if success:
            success_count += 1
        else:
            fail_count += 1
        
        # 可选：添加延迟避免请求过快
        await asyncio.sleep(1)
    
    print(f"\n处理完成！成功: {success_count}, 失败: {fail_count}")

if __name__ == "__main__":
    asyncio.run(main())