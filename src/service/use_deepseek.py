import json
import pickle
from pathlib import Path
from typing import List

import tomllib
from openai import OpenAI
from src.util.config_util import load_config

# ==============================================================================
# 配置加载
# ==============================================================================


config = load_config()

OCR_DIR = Path(config.rag.ocr_dir)
OUTPUT_FILE = Path(config.rag.output_file)

client = OpenAI(
    api_key=config.llm.api_key.get_secret_value(), base_url=config.llm.base_url
)

MODEL = config.llm.model


# ==============================================================================
# Prompt（结构化约束）
# ==============================================================================

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


# ==============================================================================
# LLM结构化
# ==============================================================================


def structure_document(text: str, system_prompt: str) -> dict:
    document = {"content": text}

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(document, ensure_ascii=False)},
        ],
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)  # type: ignore
    except Exception:
        raise ValueError(f"模型输出非JSON：{content}")


test_json = """
{'designer_or_company': {'type': 'company', 'name': '宇帆国际建筑规划设计（深圳）有限公司', 'team_intro': '由资深设计师李雄敏先生创立，专业深耕与文旅规划、建筑设计、室内设计等版块提供设计及顾问服务，精英团队以其卓越的设计专业知识、丰富的国际化经验以及卓著的管理技术，为客户提供优质的服务和产品。', 'honors': [], 'members': [{'name': '李雄敏', 'title': '创始人', 'expertise': None, 'education': None, 'experience': None, 'bio': None}], 'services': ['文旅规划', '建筑设计', '室内设计'], 'clients_partners': ['平安', '万豪', '恒大', '雅高', '绿地', '四季', '万科', 'HBA', 'NIKKN', 'KPF']}, 'projects': [{'name': '迎日产业循环经济园总体规划', 'category': '城市规划', 'subcategory': '产业园区', 'nature': '规划方案', 'role': None, 'responsibilities': [], 'location': None, 'area': '2.78平方公里', 'area_detail': {'total_area': '2.78平方公里', 'building_area': None, 'green_area': None, 'other_metrics': None}, 'year': None, 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['循环经济', '产业园区', '总体规划']}, {'name': '吉隆坡北斗大廈', 'category': '建筑设计', 'subcategory': '超高层', 'nature': None, 'role': None, 'responsibilities': [], 'location': '吉隆坡', 'area': '20万㎡', 'area_detail': {'total_area': None, 'building_area': '20万', 'green_area': None, 'other_metrics': None}, 'year': '2023', 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['地标', '超高层']}, {'name': '楚雄彝风湿地文旅小镇', 'category': '建筑设计', 'subcategory': '文旅小镇', 'nature': None, 'role': None, 'responsibilities': [], 'location': '楚雄', 'area': '7万㎡', 'area_detail': {'total_area': None, 'building_area': '7万', 'green_area': None, 'other_metrics': None}, 'year': '2020', 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['文旅', '小镇']}, {'name': '武汉城市驿站', 'category': '建筑设计', 'subcategory': None, 'nature': None, 'role': None, 'responsibilities': [], 'location': '武汉', 'area': '1000㎡', 'area_detail': {'total_area': None, 'building_area': '1000', 'green_area': None, 'other_metrics': None}, 'year': None, 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['驿站', '公共建筑']}, {'name': '北京四季酒店', 'category': '建筑设计', 'subcategory': '酒店', 'nature': None, 'role': None, 'responsibilities': [], 'location': '北京', 'area': '43000㎡', 'area_detail': {'total_area': None, 'building_area': '43000', 'green_area': None, 'other_metrics': None}, 'year': '2011', 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['酒店', '豪华']}, {'name': '大同福朋喜来登酒店', 'category': '建筑设计', 'subcategory': '酒店', 'nature': None, 'role': None, 'responsibilities': [], 'location': '大同', 'area': '14000㎡', 'area_detail': {'total_area': None, 'building_area': '14000', 'green_area': None, 'other_metrics': None}, 'year': '2011', 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['酒店', '喜来登']}, {'name': '深圳众冠时代广场', 'category': '建筑设计', 'subcategory': '商业综合体', 'nature': None, 'role': None, 'responsibilities': [], 'location': '深圳', 'area': '60000㎡', 'area_detail': {'total_area': None, 'building_area': '60000', 'green_area': None, 'other_metrics': None}, 'year': '2016', 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['商业综合体', '购物中心']}, {'name': '深圳平安国际金融中心', 'category': '建筑设计', 'subcategory': '超高层', 'nature': None, 'role': None, 'responsibilities': [], 'location': '深圳', 'area': '35000㎡', 'area_detail': {'total_area': None, 'building_area': '35000', 'green_area': None, 'other_metrics': None}, 'year': '2016', 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['地标', '超高层', '金融']}, {'name': '贵州臻大悦湖印象', 'category': '建筑设计', 'subcategory': '住宅', 'nature': None, 'role': None, 'responsibilities': [], 'location': '贵州', 'area': '1200㎡', 'area_detail': {'total_area': None, 'building_area': '1200', 'green_area': None, 'other_metrics': None}, 'year': None, 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['住宅', '湖景']}, {'name': '广州凯达尔国际枢纽广场', 'category': '建筑设计', 'subcategory': '交通枢纽', 'nature': None, 'role': None, 'responsibilities': [], 'location': '广州', 'area': '7000㎡', 'area_detail': {'total_area': None, 'building_area': '7000', 'green_area': None, 'other_metrics': None}, 'year': '2017', 'client': None, 'client_type': None, 'description': None, 'status': None, 'collaborators': [], 'tags': ['枢纽', '商业', '地标']}]}
"""

from src.util.config_util import load_config
from src.database.mongodb_client import MongodbClient


async def main() -> None:
    result = structure_document(
        r"宇帆国际LIONINGSUNDESIGNCOMPANY PROFILE宇帆国际建筑规划设计（深圳）有限公司（以下简称K11），由资深设计师李雄敏先生创立，专业深耕与文旅规划、建筑设计、室内设计等版块提供设计及顾问服务，K11的精英团队以其卓越的设计专业知识丰富的国际化经验以及卓著的管理技术，蓄势待发，为客户提供优质的服务和产品。K11的国际化的团队及其专业技术另其与时俱进，在行业内始终保持领先位置及前瞻性的创新。近年来，中国室内设计行业蓬勃发展，K11先后多次与HBA、NIKKN、KPF等知名设计事务所合作，成功案例遍布全国，同时先后为平安、万豪、恒大、雅高、绿地、四季、万科等知名地产及酒店管理公司成功的提供了设计及顾问服务工作。宇帆国际LIONINGSUN DESIGN过往知名代表项目展示郑州千禧广场（地标）深圳平安国际金融中心（地标）吉隆坡北斗大厦广州凯达尔国际枢纽广场（深圳众冠时代广场深圳自贸中心建筑（规划）设计代表项目展示建筑（规划）设计文旅规划设计马市工业园区竹产业循环经济园总体规划龙岩古木督景区吉隆坡北斗大廈惠州巽寮湾国防教育研学基地广州凯达尔国际枢纽广场深圳麻勘村度假基地韶关露营基地湛江华双济海贵州臻大悦湖印象楚雄彝风湿地文旅小镇怀仁雲州公馆深圳职业病防治院办公楼黄梅四合院武汉城市驿站武汉体育馆酒店烟台金都购物广场室内设计代表项目展示酒店/公寓办公/会所地产/购物中心/学校上海王宝和大酒店郑州千禧广场湛江华双济海北京四季酒店深圳众冠时代广场贵州臻大·悦湖印象武汉江城豪生酒店深圳自贸中心清远十里湖山深圳平安国际金融中心义乌万达嘉华酒店（设计研发）楚雄彝风湿地文旅小镇广州凯达尔国际枢纽广场天津恒大名都综合体怀仁雲州公馆上海外马路私人会所天津恒大绿洲综合体西安金辉世界城云南楚雄会所广州凯达尔万豪酒店武汉金域国际商场大连城堡酒店宝安曦城别墅会所广州凯达尔国际枢纽广场大同福朋喜来登酒店龙岗十二橡树别墅会所深圳泰宁小学深圳众冠时代广场公寓凯达尔国际枢纽广场会所广州凯达尔国际公寓大同福朋喜来登酒店会所迎日产业循环经济园总体规划规划设计面积：2.78平方公里设计时间马市工业园区竹产业管环经济园吉隆坡北斗大廈建筑设计面积：20万设计时间：2023I2A广州凯达尔国际枢纽广场4t楚雄彝风湿地文旅小镇建筑设计面积：7万设计时间：2020武汉城市驿站建筑设计面积：1000设计时间：202NSTAREN心C中在民方R北京四季酒店建筑设计面积：43000设计时间：2011DFOURYPOINTSBY SHERATON大同福朋喜来登酒店大同福朋喜来登酒店建筑设计面积：14000设计时间ES11T门设计时建筑设计面积：38000m上广州凯达尔万豪酒店X17一凯达尔国际公寓KAIDAER CHI NGJI二APARTMENT凯达尔城际公寓八东#\EANMENTI冠1深圳众冠时代广场建筑设计面积：60000设计时间：2016众冠时代购石保守机密慎之又慎。毛汽车建筑设计面积10000 设计时间：2017厂深圳自贸中心THLTisunTinSunAOE深圳平安国际金融中心建筑设计面积：35000设计时间：2016进线大同福朋喜来登酒店会所建筑设计面积16贵州臻大悦湖印象建筑设计面积：1200mEAnnANNNNNT新2福臻大·悦湖印象工+干饭t>126户型主卧空间囍牌日广场建筑设计面积：7000m设计时间：201712二二SHENZHEN深圳LOCK B, JIHONG BuILDING,1 BINGLANG ROAD,FUTIAN FREE TRADE ZONE, SHENZHEN深圳市福田保税区槟榔路1号吉虹大厦B座TEL:18920093008",
        MONGODB_PROMPT,
    )
    config = load_config()
    mongo = MongodbClient(config)
    await mongo.insert_json_string("newspace_documents", "newspace", json.dumps(result))
    print(result)


import asyncio

if __name__ == "__main__":
    asyncio.run(main())

# ==============================================================================
# Embedding
# ==============================================================================
