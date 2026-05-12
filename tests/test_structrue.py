import json
import pickle
from pathlib import Path
from typing import List

import tomllib
from openai import OpenAI


# ==============================================================================
# 配置加载
# ==============================================================================

def load_config():
    with open("config.toml", "rb") as f:
        return tomllib.load(f)


config = load_config()

OCR_DIR = Path(config["rag"]["ocr_dir"])
OUTPUT_FILE = Path(config["rag"]["output_file"])

client = OpenAI(
    api_key=config["llm"]["api_key"],
    base_url=config["llm"]["base_url"]
)

MODEL = config["llm"]["model"]


# ==============================================================================
# Prompt（结构化约束）
# ==============================================================================

SYSTEM_PROMPT = """
你是文档结构化引擎，只做信息抽取，不允许推理或编造。

输出必须是严格JSON，禁止任何解释。

规则：
1. 所有字段必须存在，不确定填 null
2. chunk content 必须是原文原句，不可改写
3. 不允许总结或扩写
4. chunks 必须来自原文连续片段

结构：
- document_type: 合同/报告/设计方案/宣传册/其他
- metadata: title, project_name, party_a, party_b, city, tags
- chunks: chunk_id, section_title, content, keywords
"""


# ==============================================================================
# LLM结构化
# ==============================================================================

def structure_document(file_name: str, text: str) -> dict:
    document = {
        "file_name": file_name,
        "content": text
    }

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(document, ensure_ascii=False)}
        ]
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content) # type: ignore
    except Exception:
        raise ValueError(f"模型输出非JSON：{content}")


# ==============================================================================
# Embedding
# ==============================================================================



# ==============================================================================
# 主流程（结构化数据构建）
# ==============================================================================

def build_dataset():
    dataset = []

    files = sorted(OCR_DIR.glob("*.txt"))
    print(f"发现 {len(files)} 个文件")

    for i, file_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {file_path.name}")

        try:
            text = file_path.read_text(encoding="utf-8").strip()

            if not text:
                continue

            structured = structure_document(file_path.name, text)

            chunks = structured.get("chunks", [])

            for chunk in chunks:
                content = chunk.get("content", "").strip()

                if not content:
                    continue

                dataset.append({
                    "file_name": file_path.name,
                    "document_type": structured.get("document_type"),
                    "metadata": structured.get("metadata"),
                    "chunk_id": chunk.get("chunk_id"),
                    "section_title": chunk.get("section_title"),
                    "keywords": chunk.get("keywords"),
                    "content": content,
                    
                })

        except Exception as e:
            print(f"失败: {file_path.name} -> {e}")
            continue

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump(dataset, f)

    print(f"\n完成：{len(dataset)} chunks")
    print(f"输出路径：{OUTPUT_FILE.resolve()}")


# ==============================================================================
# 入口
# ==============================================================================

if __name__ == "__main__":
    build_dataset()