from paddleocr import PaddleOCR
import pytest

@pytest.mark.test_ocr
async def test_ocr():
    ocr = PaddleOCR(
        use_angle_cls=True,
        lang="ch",
        device="gpu"
    )
    results = ocr.predict("./static/test3.pdf")
    all_text = []
    for res in results:
        texts = res['rec_texts']
        all_text.extend(texts)
    final_text = "\n".join(all_text)
    print(final_text)