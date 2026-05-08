import json
from paddleocr import PPStructureV3
import pytest

@pytest.mark.paddle_struct
async def test_struct_model():
    def save_text_as_json(result, save_path):
        # 提取所有区块的文字
        all_true_text = []
        all_text = []
        for res in result:
            for block in res['parsing_res_list']:
                all_true_text.append(block)
                all_text.append(block.content)   # 使用 .content 属性
        full_text = '\n'.join(all_text)
        print(full_text)
        with open(f"{save_path}.json", 'w', encoding='utf-8') as f:
            json.dump({"text": full_text}, f, ensure_ascii=False, indent=2)

    # 使用
    pipeline = PPStructureV3(device="gpu")
    output = pipeline.predict("./static/test2.pdf")
    save_text_as_json(output, "output")   # 生成 output.json