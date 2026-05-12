from src.util.config_util import load_config
from src.database.mongodb_client import MongodbClient
from src.service.use_deepseek import *
from pathlib import Path
import asyncio
import pickle
import os

MONGODB_PROMPT = """
你是一个专业的数据提取助手。你的任务是从给定的宣传册/作品集文本中，提取【设计师/团队信息】和【项目信息】，并严格按照下面的 JSON 格式输出。

### 输出格式要求
输出必须是一个合法的 JSON 对象，不要包含任何解释、注释或额外文字。缺失的字段用 null 表示，缺失的数组用 [] 表示。禁止编造原文不存在的内容。

### 字段定义

#### designer_or_company 对象（团队或个人介绍）
- type: 判断是公司还是个人，可选值 "company" 或 "individual"
- name: 公司全称或个人姓名（string 或 null）
- team_intro: 团队/个人的整体介绍、理念、价值观等（string 或 null）
- honors: 获奖、荣誉、参与制定的标准等（array of string）
- members: 团队成员列表（如果是个人作品集，成员通常只有1人）：
    - name: 姓名（string）
    - title: 职位/角色（string 或 null）
    - expertise: 专长领域（string 或 null）
    - education: 教育背景（学校+专业）（string 或 null）
    - experience: 从业经历、工作年限、服务过的公司等（string 或 null）
    - bio: 个人简介（其他描述）（string 或 null）
- services: 服务范围/业务领域列表，如 ["室内设计", "软装设计", "灯光设计"]（array of string）
- clients_partners: 合作过的客户或战略合作伙伴，如 ["万科", "华润"]（array of string）

#### projects 数组（项目信息）
每个项目是一个对象，按出现顺序提取：

- name: 项目全称（string）
- category: 项目主类别，从以下选择最匹配的：
    "建筑设计" / "室内设计" / "景观设计" / "城市规划" / "文旅策划" / 
    "IP形象设计" / "品牌设计" / "绘画" / "产品设计" / "商业展示" / "其他"
    如果不属于以上，保留原文描述（string 或 null）
- subcategory: 细分类型，如 "商业综合体" / "住宅小区" / "屋顶花园" / "美食城" / "写字楼"（string 或 null）
- nature: 项目性质，如 "新建" / "改造" / "规划方案" / "提升优化" / "概念设计"（string 或 null）
- role: 参与角色，如 "主创" / "主要参与" / "配合" / "独立完成"（string 或 null）
- responsibilities: 主要负责内容列表，如 ["方案整体构思", "总平面图", "节点设计"]（array of string）
- location: 地点，精确到市/区（string 或 null）
- area: 面积/规模的简要描述，如 "3.8万㎡" 或 "91亩"（string 或 null）
- area_detail: 详细的面积指标，包含以下子字段（可选）：
    - total_area: 总用地面积（string 或 null）
    - building_area: 建筑面积（string 或 null）
    - green_area: 绿地面积（string 或 null）
    - other_metrics: 其他指标，如 "容积率1.6" / "床位200张"（string 或 null）
- year: 年份，优先提取设计年份/委托年份/建成时间（string 或 null）
- client: 客户/建设方/业主名称（string 或 null）
- client_type: 客户类型，从以下选择："政府" / "开发商" / "企业" / "个人" / "其他"（string 或 null）
- description: 项目简介、设计理念、亮点、特色功能等（string 或 null）
- status: 状态，如 "已建成" / "在建" / "设计中" / "概念方案"（string 或 null）
- collaborators: 合作单位或个人，如 "中国美术学院风景建筑设计院" / "户田芳树"（array of string）
- tags: 关键词标签，从文本中提炼2-5个，如 ["康养", "适老化", "CCRC"]（array of string）

### 提取规则

1. **判断是公司还是个人**：
   - 如果出现"我们""团队""公司"等集体称呼，且有多个成员介绍，标记为 "company"
   - 如果只有一个名字，或者出现"个人简介""教育背景""从业经历"，标记为 "individual"

2. **提取会员信息**：
   - 公司宣传册：提取所有提到姓名+职位的人员
   - 个人作品集：通常只有一个人，姓名从顶部/底部/文件名中提取

3. **项目分类识别**：
   - 留意章节标题：如"主创项目""主要参与项目""其他作品" —— 这些对应 role 字段
   - 留意"主要负责内容"后面的列表 —— 对应 responsibilities 字段

4. **项目性质识别**：
   - 出现"改造""翻新""提升"等词 → nature = "改造"
   - 出现"新建""新建工程"等词 → nature = "新建"
   - 出现"规划""概念规划"等词 → nature = "规划方案"

5. **面积处理**：
   - 优先提取带单位的数字（㎡ / 平方米 / 亩 / 公顷）
   - 如果有详细拆分的，填充 area_detail 的子字段
   - 否则简单填充 area 字段

6. **年份提取**：
   - 识别格式：20XX年 / XXXX年 / 202X
   - 注意上下文的"委托时间""设计时间""建成时间"

7. **项目独立性判断**：
   - 如果一个页面/章节有多个项目标题，逐个拆分
   - 如果某个项目下有子项目（如"雄安新区中央绿谷规划"下的"未来畔"），
     优先作为独立项目提取，同时在 name 中体现层级，如"雄安新区中央绿谷规划·未来畔"

8. **没有的信息**：字段缺失时用 null 或 []，不要自己编造

### 输出示例（仅作格式参考）

{
  "designer_or_company": {
    "type": "company",
    "name": "横竖建筑工作室",
    "team_intro": "国际视野的新锐建筑工作室，专注于城市微更新和新田园主义实践",
    "honors": [],
    "members": [
      {
        "name": "蓝福兵",
        "title": "合伙人",
        "expertise": "建筑设计",
        "education": "广西英华学院，环境艺术设计专业",
        "experience": "15年设计经验，经历6家外企和港资建筑室内设计公司",
        "bio": null
      }
    ],
    "services": ["建筑设计", "景观设计", "室内设计", "品牌设计"],
    "clients_partners": ["华润", "旭辉", "新鸿基", "万科"]
  },
  "projects": [
    {
      "name": "山东烟台新城吾悦广场",
      "category": "室内设计",
      "subcategory": "商业综合体",
      "nature": "新建",
      "role": "主创",
      "responsibilities": ["室内方案设计"],
      "location": "中国烟台",
      "area": "16000平方米",
      "area_detail": {
        "total_area": null,
        "building_area": "16000",
        "green_area": null,
        "other_metrics": null
      },
      "year": null,
      "client": "新城控股集团",
      "client_type": "开发商",
      "description": "打造'运动甲板'特色主题空间，卡路里公园概念",
      "status": "已建成",
      "collaborators": [],
      "tags": ["商业", "运动主题", "卡路里公园"]
    }
  ]
}

### 现在，请根据以下宣传册/作品集文本输出 JSON：
"""

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