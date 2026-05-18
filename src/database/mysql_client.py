from typing import List

import aiomysql

from src.model.config_model import Config


class MySQLClient:
    """mysql客户端,使用前需要init(因为创建函数是异步,而类的__init__不能是异步)"""

    pool: aiomysql.Pool

    async def init(self, config: Config):
        self.pool = await aiomysql.create_pool(
            host=config.database.mysql.url,
            port=config.database.mysql.port,
            user=config.database.mysql.username,
            password=config.database.mysql.password,
            db=config.database.mysql.db,
            autocommit=False,
        )

    async def ping_mysql(self) -> bool:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 10")
                # print(cur.description)
                (r,) = await cur.fetchone()
                if r == 10:
                    return True
        return False

    async def get_tags(self) -> List:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id, parent_id ,name From new_tag")
                r = await cur.fetchall()
                return r

    async def get_all_pdf_info(self) -> List:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT * from new_team_case WHERE type = "pdf"')
                r = await cur.fetchall()
                return r

    async def get_pdf_info(self, file_id: str):
        """应该返回(tream_id, name, path)"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT team_id, name, path FROM new_team_case WHERE id = %s",
                    (file_id,),
                )
                r = await cur.fetchone()
                return r

    async def get_all_fav_pdf_info(self) -> List:
        """应该返回(tream_id, name, path)"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM new_team_fav_case WHERE type = 'pdf'",
                )
                r = await cur.fetchall()
                return r
            
    async def get_fav_pdf_info(self, file_id: str):
        """应该返回(team_id, name, path)"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT team_id, name, path, id FROM new_team_fav_case WHERE id = %s",
                    (file_id,),
                )
                r = await cur.fetchone()
                return r
