from typing import Dict, List, Tuple
from pydantic import BaseModel, ConfigDict
from src.database.mysql_client import MySQLClient
from src.database.redis_client import RedisClient
from src.model.config_model import Config

class AppState(BaseModel):
    """app.state的类型,仅用于类型提示"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    config: Config
    mysql: MySQLClient
    redis: RedisClient  
    tags: Tuple[Dict[str, int], Dict[str, List[str]]] #数据库里的相关tags