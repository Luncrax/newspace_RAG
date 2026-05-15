from paddleocr import PaddleOCR

from paddleocr import PaddleOCR

ocr = PaddleOCR(
    # 基础配置
    lang='ch',  # 中文
    use_doc_orientation_classify=False,  # 文档方向分类（节省内存）
    use_doc_unwarping=False,  # 文档展平（节省内存）
    use_textline_orientation=False,  # 文本行方向检测（节省内存）
    
    # GPU内存优化关键参数
    text_det_limit_side_len=640,  # 检测图像边长限制（原 det_limit_side_len）
    text_det_limit_type='max',  # 限制类型
    text_det_thresh=0.3,  # 检测阈值
    text_det_box_thresh=0.5,  # 文本框阈值
    text_det_unclip_ratio=2.0,  # 扩张比例
    
    # 识别批处理大小（控制内存）
    text_recognition_batch_size=1,  # 每批处理1张图（原 batch_size）
    
    # 其他优化
    text_rec_score_thresh=0.5,  # 识别分数阈值
    return_word_box=False,  # 不返回单词级框（节省内存）
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