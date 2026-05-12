from openai import OpenAI
import pytest

@pytest.mark.test_deepseek
def test_deepseek():
    client = OpenAI(
        api_key="sk-87c5b57f594a46649de9fe420d2fc906",
        base_url="https://api.deepseek.com/v1"
    )

    res = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role":"user","content":"hello"}]
    )

    print(res.choices[0].message.content)