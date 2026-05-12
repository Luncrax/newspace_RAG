import paddle
import pytest

@pytest.mark.test_gpu
async def test_gpu():
    paddle.utils.run_check()