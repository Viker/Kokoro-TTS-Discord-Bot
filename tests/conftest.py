import pytest
from kokoro_bot.core.config import Config
from kokoro_bot.utils.result import Result

@pytest.fixture
def config():
    return Config("tests/test_config.yaml")

@pytest.fixture
def result():
    return Result