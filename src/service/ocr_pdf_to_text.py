from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_angle_cls=False,
    lang="ch",
    device="gpu",

)

def pdf_to_text(path: str) -> str:
    results = ocr.predict(path)
    all_text = []
    for res in results:
        texts = res['rec_texts']
        all_text.extend(texts)
    final_text = "".join(all_text)
    print(final_text)
    return final_text