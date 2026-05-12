# scripts/merge_markdown.py

from pathlib import Path
import re


def extract_number(file_path: Path) -> int:
    """
    从文件名中提取序号。

    示例：
        test3_1.md   -> 1
        test3_12.md  -> 12
    """
    match = re.search(r"test3_(\d+)\.md$", file_path.name)
    if not match:
        return 999999999
    return int(match.group(1))


def merge_markdown():
    output_dir = Path("output")
    merged_file = output_dir / "test3_merged.md"

    # 找到所有 test3_*.md 文件（排除最终合并文件）
    md_files = [
        f for f in output_dir.glob("test3_*.md")
        if f.name != "test3_merged.md"
    ]

    # 按数字序号排序
    md_files.sort(key=extract_number)

    print(f"找到 {len(md_files)} 个 Markdown 文件")

    # 合并内容
    with merged_file.open("w", encoding="utf-8") as outfile:
        for md_file in md_files:
            print(f"合并: {md_file.name}")

            content = md_file.read_text(encoding="utf-8").strip()

            # 写入文件内容
            outfile.write(content)

            # 文件之间添加两个换行
            outfile.write("\n\n")

    print(f"合并完成: {merged_file}")


if __name__ == "__main__":
    merge_markdown()