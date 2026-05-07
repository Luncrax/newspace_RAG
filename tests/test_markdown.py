import json
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_angle_cls=True,
    lang="ch",
    device="gpu"
)

results = ocr.predict("./static/test2.pdf")

documents = []

for page_idx, res in enumerate(results):

    texts = res.get("rec_texts", [])

    # 清洗文本
    clean_texts = []

    for text in texts:

        text = str(text).strip()

        # 过滤空行
        if not text:
            continue

        # 过滤超短乱码
        if len(text) == 1:
            continue

        clean_texts.append(text)

    page_text = "\n".join(clean_texts)

    documents.append({
        "page": page_idx + 1,
        "text": page_text
    })

# 整本文档
full_text = "\n\n".join(
    [doc["text"] for doc in documents]
)

print(full_text)

# 保存 JSON
with open("output.json", "w", encoding="utf-8") as f:

    json.dump(
        {
            "full_text": full_text,
            "pages": documents
        },
        f,
        ensure_ascii=False,
        indent=2
    )

print("OCR完成，已保存 output.json")