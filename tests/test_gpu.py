import paddle
import pytest
@pytest.mark.gpu

async def test_gpu():
    paddle.utils.run_check()