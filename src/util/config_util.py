from src.model.config_model import *
import tomllib
import tomli_w
import os
import logging

CONFIG_PATH = "config.toml" #配置文件路径

def create_config():
    """重置配置文件"""
    cfg = Config()
    data = cfg.model_dump()
    data["llm"]["api_key"] = ""
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(data, f)
        logging.info("初始化配置文件")
    return cfg


def load_config() -> Config:
    """加载配置文件"""
    if not os.path.exists(CONFIG_PATH):
        create_config()
        raise Exception("配置文件错误,已初始化")

    with open(CONFIG_PATH, "rb") as f:
        data = tomllib.load(f)
    try:
        cfg = Config(**data)
    except:
        with open("config_bak.toml", "wb") as f:
            tomli_w.dump(data, f)
        logging.info("检测到配置有问题,已重置和备份")
        create_config()
    return cfg