from pathlib import Path
import pickle
import os

from paddleocr import PaddleOCR

from src.service.ocr_pdf_to_text import pdf_to_text

PROCESSED_FILE = Path("./data/ocr_processed.pkl")

PDF_DIR = Path("./data/download_pdfs")

OUTPUT_DIR = Path("./data/ocr_finished_team_pdf")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_processed_files() -> set[str]:
    """
    加载已处理文件集合
    """
    if not PROCESSED_FILE.exists():
        return set()

    with open(PROCESSED_FILE, "rb") as f:
        return pickle.load(f)


def save_processed_files(processed_files: set[str]) -> None:
    """
    保存已处理集合
    """
    with open(PROCESSED_FILE, "wb") as f:
        pickle.dump(processed_files, f)


def main() -> None:
    # 所有文件
    all_files = {
        file.name: file
        for file in PDF_DIR.iterdir()
        if file.is_file()
    }

    # 已处理
    processed_files = load_processed_files()

    # 差集
    need_process = set(all_files.keys()) - processed_files

    print(f"总文件数: {len(all_files)}")
    print(f"已处理: {len(processed_files)}")
    print(f"待处理: {len(need_process)}")

    for filename in need_process:
        file = all_files[filename]

        try:
            print(f"\n开始 OCR: {filename}")

            # 提取前面的数字
            number = file.stem.split("_")[0]

            # OCR
            text = pdf_to_text(str(file))

            # 输出 txt
            output_file = OUTPUT_DIR / f"{number}.txt"

            # 追加写入
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 30}\n")
                f.write(f"FILE: {filename}\n")
                f.write(f"{'=' * 30}\n\n")
                f.write(text)
                f.write("\n\n")

            # 加入已处理集合
            processed_files.add(filename)

            # 实时保存
            save_processed_files(processed_files)

            print(f"OCR 完成: {filename}")

        except Exception as e:
            print(f"OCR 失败: {filename}")
            print(type(e).__name__, e)


if __name__ == '__main__':
    main()