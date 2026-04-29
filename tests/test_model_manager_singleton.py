"""Process-wide BedrockModel singleton in model_manager."""

from unittest.mock import MagicMock, patch

import pytest

from smart_report_analyst.service.bedrock import model_manager as mm


@pytest.fixture(autouse=True)
def _clear_singleton():
    mm.clear_process_bedrock_model_cache()
    yield
    mm.clear_process_bedrock_model_cache()


@patch.object(mm, "get_settings")
@patch.object(mm, "BedrockModel")
def test_get_process_bedrock_model_returns_same_instance(mock_bedrock_cls, mock_get_settings):
    mock_get_settings.return_value = MagicMock(
        BEDROCK_MODEL_ID="us.anthropic.fake",
        AWS_REGION="us-east-1",
    )
    a = MagicMock()
    b = MagicMock()
    mock_bedrock_cls.side_effect = [a, b]

    first = mm.get_process_bedrock_model()
    second = mm.get_process_bedrock_model()

    assert first is second is a
    mock_bedrock_cls.assert_called_once()


@patch.object(mm, "get_settings")
@patch.object(mm, "BedrockModel")
def test_clear_cache_rebuilds(mock_bedrock_cls, mock_get_settings):
    mock_get_settings.return_value = MagicMock(
        BEDROCK_MODEL_ID="us.anthropic.fake",
        AWS_REGION="us-east-1",
    )
    m1, m2 = MagicMock(), MagicMock()
    mock_bedrock_cls.side_effect = [m1, m2]

    assert mm.get_process_bedrock_model() is m1
    mm.clear_process_bedrock_model_cache()
    assert mm.get_process_bedrock_model() is m2
    assert mock_bedrock_cls.call_count == 2


@patch.object(mm, "get_settings")
def test_missing_model_id_raises(mock_get_settings):
    mock_get_settings.return_value = MagicMock(BEDROCK_MODEL_ID=None, AWS_REGION="us-east-1")
    with pytest.raises(ValueError, match="BEDROCK_MODEL_ID"):
        mm.get_process_bedrock_model()
