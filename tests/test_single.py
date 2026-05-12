import json
from pathlib import Path

from tests.test_structrue import (
    structure_document,
    OCR_DIR
)


def test_one_file():
    files = sorted(OCR_DIR.glob("*.txt"))

    if not files:
        print("没有找到文件")
        return

    file_path = files[0]
    print(f"测试文件: {file_path.name}")

    text = file_path.read_text(encoding="utf-8").strip()

    if not text:
        print("文件为空")
        return

    # 1️⃣ 结构化
    structured = structure_document(file_path.name, text)

    print("\n===== 结构化完成 =====")

    # 2️⃣ 保存 JSON
    output_path = Path("tests/output_single.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)

    print(f"\n已保存到: {output_path.resolve()}")


if __name__ == "__main__":
    test_one_file()