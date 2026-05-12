from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import time
from typing import Any, Dict, List, Optional, Union
from src.util.config_util import *

class MongodbClient:
    client: AsyncIOMotorClient

    def __init__(self, config: Config) -> None:
        # 构建连接字符串
        connection_string = (
            f"mongodb://{config.database.mongodb.username}:{config.database.mongodb.password}"
            f"@{config.database.mongodb.host}:{config.database.mongodb.port}/"
            f"?authSource={config.database.mongodb.authSource}"
        )
        self.client = AsyncIOMotorClient(connection_string)
        
        # 可选：设置连接超时等参数
        # self.client = AsyncIOMotorClient(
        #     connection_string,
        #     serverSelectionTimeoutMS=5000,  # 服务器选择超时
        #     connectTimeoutMS=10000,          # 连接超时
        #     maxPoolSize=50,                  # 连接池大小
        # )

    async def ping(self) -> bool:
        """测试数据库连接是否正常"""
        try:
            # 使用 admin 数据库的 ping 命令
            await self.client.admin.command('ping')
            print("✅ MongoDB 连接正常")
            return True
        except Exception as e:
            print(f"❌ MongoDB 连接失败: {e}")
            return False

    async def get_database(self, db_name: str):
        """获取数据库实例"""
        if db_name:
            return self.client[db_name]
        return self.client.get_default_database()

    async def get_collection(self, collection_name: str, db_name: str):
        """获取集合实例"""
        db = await self.get_database(db_name)
        return db[collection_name]

    async def close(self):
        """关闭连接"""
        self.client.close()
        print("🔒 MongoDB 连接已关闭")

    # 通用 JSON 插入方法
    async def insert_one(self, collection_name: str, db_name: str, document: Dict[str, Any]) -> str:
        """
        插入单条 JSON 文档到 MongoDB
        
        Args:
            collection_name: 集合名称
            db_name: 数据库名称
            document: 要插入的 JSON 文档（字典格式）
            
        Returns:
            插入文档的 _id
        """
        try:
            collection = await self.get_collection(collection_name, db_name)
            
            # 可选：自动添加时间戳
            if 'created_at' not in document:
                document['created_at'] = datetime.now()
            
            result = await collection.insert_one(document)
            print(f"✅ 成功插入文档，ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            print(f"❌ 插入文档失败: {e}")
            raise

    async def insert_many(self, collection_name: str, db_name: str, documents: List[Dict[str, Any]]) -> List[str]:
        """
        批量插入多条 JSON 文档到 MongoDB
        
        Args:
            collection_name: 集合名称
            db_name: 数据库名称
            documents: 要插入的 JSON 文档列表
            
        Returns:
            插入文档的 _id 列表
        """
        try:
            collection = await self.get_collection(collection_name, db_name)
            
            # 可选：为每个文档自动添加时间戳
            for doc in documents:
                if 'created_at' not in doc:
                    doc['created_at'] = datetime.now()
            
            result = await collection.insert_many(documents)
            inserted_ids = [str(id) for id in result.inserted_ids]
            print(f"✅ 成功批量插入 {len(inserted_ids)} 条文档")
            return inserted_ids
        except Exception as e:
            print(f"❌ 批量插入文档失败: {e}")
            raise

    async def insert_or_update(self, collection_name: str, db_name: str, 
                                filter_criteria: Dict[str, Any], 
                                document: Dict[str, Any],
                                upsert: bool = True) -> str:
        """
        插入或更新文档（如果存在则更新，不存在则插入）
        
        Args:
            collection_name: 集合名称
            db_name: 数据库名称
            filter_criteria: 查询条件（用于判断文档是否存在）
            document: 要插入/更新的文档
            upsert: 如果为 True，不存在时则插入
            
        Returns:
            操作结果的 _id
        """
        try:
            collection = await self.get_collection(collection_name, db_name)
            
            # 添加更新时间戳
            document['updated_at'] = datetime.now()
            if 'created_at' not in document:
                document['created_at'] = datetime.now()
            
            # 使用 $set 进行更新操作
            result = await collection.update_one(
                filter_criteria,
                {'$set': document},
                upsert=upsert
            )
            
            if result.upserted_id:
                print(f"✅ 成功插入新文档，ID: {result.upserted_id}")
                return str(result.upserted_id)
            else:
                print(f"✅ 成功更新文档，匹配数: {result.matched_count}")
                # 返回查询到的文档 ID
                existing = await collection.find_one(filter_criteria)
                return str(existing['_id']) if existing else ""
        except Exception as e:
            print(f"❌ 插入或更新文档失败: {e}")
            raise

    async def insert_json_string(self, collection_name: str, db_name: str, json_string: str) -> str:
        """
        插入 JSON 字符串到 MongoDB（自动解析）
        
        Args:
            collection_name: 集合名称
            db_name: 数据库名称
            json_string: JSON 格式的字符串
            
        Returns:
            插入文档的 _id
        """
        import json
        try:
            # 解析 JSON 字符串
            document = json.loads(json_string)
            return await self.insert_one(collection_name, db_name, document)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            raise
        except Exception as e:
            print(f"❌ 插入失败: {e}")
            raise

    # 原有的插入传感器数据方法
    async def insert_sensor_data(self, collection_name: str, sensor_id: str, 
                                  temperature: float, humidity: float):
        """插入传感器数据到时间序列集合"""
        collection = await self.get_collection(collection_name, "iot_db")
        
        data = {
            "timestamp": datetime.now(),
            "sensor_id": sensor_id,
            "temperature": temperature,
            "value": temperature
        }
        if humidity:
            data["humidity"] = humidity
        
        result = await collection.insert_one(data)
        return result.inserted_id

    # 示例：查询最新数据
    async def get_latest_data(self, collection_name: str, limit: int = 10):
        """获取最新的 N 条数据"""
        collection = await self.get_collection(collection_name, "iot_db")
        cursor = collection.find().sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)