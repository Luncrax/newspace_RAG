from pydantic import BaseModel, SecretStr


class Server(BaseModel):
    """fastapi服务端配置"""
    host: str = "0.0.0.0"
    port: int = 54080

class MySql(BaseModel):
    """mysql的配置"""
    url: str = ""
    port: int = 3306
    username: str = ""
    password: str = ""
    db: str = ""

class Redis(BaseModel):
    """redis的配置"""
    url: str = ""
    password: str = ""
    port: int = 6379
    db: int = 1
    stream_download: str = "stream_download"
    stream_ocr: str = "stream_ocr"
    stream_rag: str = "stream_rag"

class Milvus(BaseModel):
    """milvus的配置"""
    url: str = ""
    port: int = 19530
    username: str = ""
    password: str = ""


class Mongodb(BaseModel):
    host: str = "localhost"
    port: int = 27017
    username: str = "admin"
    password: str = ""
    authSource: str = "admin"

class Database(BaseModel):
    """数据库的配置"""
    mysql: MySql = MySql()
    redis: Redis = Redis()
    milvus: Milvus = Milvus()
    mongodb: Mongodb = Mongodb()

class Llm(BaseModel):
    """大模型的配置"""
    api_key: SecretStr = SecretStr("sk-xxxx")
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    system_prompt: str = "你是新空间的ai问答机器人,单次数回答禁止检索3次以上"

class Rag(BaseModel):
    ocr_dir: str = ""
    output_file: str = ""

class Login(BaseModel):
    """newspace的登陆配置"""
    secret: str = ""
    url: str = ""
    username: str = ""
    password: str = ""

class Config(BaseModel):
    """config主类"""
    llm: Llm = Llm()
    database: Database = Database()
    server: Server = Server()
    login: Login = Login()
    rag: Rag = Rag()
