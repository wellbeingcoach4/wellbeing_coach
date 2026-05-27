import pytest
from unittest.mock import AsyncMock, Mock, patch

from service import mood_analyser
from service.mood_analyser import MoodAnalyzerService
from app.llm.config import LLMProvider


@pytest.fixture
def mock_db():
    return Mock()


@pytest.fixture
def service(mock_db):
    svc = MoodAnalyzerService(mock_db)
    svc.primary_provider = LLMProvider.OLLAMA
    svc.fallback_provider = LLMProvider.GROQ
    return svc


@pytest.fixture
def valid_response():
    return {
        "mood_analysed": "happy",
        "reason_for_mood": "Positive words detected",
        "confidence_score": 0.95,
        "provider_used": "ollama"
    }


# =========================================================
# analyze_mood()
# =========================================================

@pytest.mark.asyncio
@patch("mood_analyser.db_repository.save_mood_analysis")
async def test_analyze_mood_success(
    mock_save,
    service,
    valid_response
):
    mock_record = Mock()
    mock_record.id = 1
    mock_save.return_value = mock_record

    service._try_llm_request = AsyncMock(return_value=valid_response)

    result = await service.analyze_mood(
        user_id="user123",
        text="I am very happy today"
    )

    assert result["mood_analysed"] == "happy"
    assert result["reason_for_mood"] == "Positive words detected"
    assert result["llm_provider"] == "ollama"
    assert result["database_id"] == 1


@pytest.mark.asyncio
@patch("mood_analyser.db_repository.save_mood_analysis")
async def test_analyze_mood_fallback_provider_used(
    mock_save,
    service,
    valid_response
):
    mock_record = Mock()
    mock_record.id = 2
    mock_save.return_value = mock_record

    service._try_llm_request = AsyncMock(
        side_effect=[
            None,
            {
                **valid_response,
                "provider_used": "groq"
            }
        ]
    )

    result = await service.analyze_mood(
        user_id="user123",
        text="Feeling anxious"
    )

    assert result["llm_provider"] == "groq"


@pytest.mark.asyncio
@patch("mood_analyser.db_repository.save_mood_analysis")
async def test_analyze_mood_all_providers_fail(
    mock_save,
    service
):
    mock_record = Mock()
    mock_record.id = 3
    mock_save.return_value = mock_record

    service._try_llm_request = AsyncMock(return_value=None)

    result = await service.analyze_mood(
        user_id="user123",
        text="test text"
    )

    assert result["mood_analysed"] == "neutral"
    assert result["llm_provider"] == "default"
    assert result["confidence_score"] == 0.0


@pytest.mark.asyncio
@patch("mood_analyser.db_repository.save_mood_analysis")
async def test_analyze_mood_invalid_response_uses_default(
    mock_save,
    service
):
    mock_record = Mock()
    mock_record.id = 4
    mock_save.return_value = mock_record

    invalid_response = {
        "mood_analysed": "",
        "reason_for_mood": ""
    }

    service._try_llm_request = AsyncMock(
        return_value=invalid_response
    )

    result = await service.analyze_mood(
        user_id="user123",
        text="test"
    )

    assert result["mood_analysed"] == "neutral"
    assert result["llm_provider"] == "default"


# =========================================================
# _try_llm_request()
# =========================================================

@pytest.mark.asyncio
async def test_try_llm_request_ollama(service):
    service._call_ollama = AsyncMock(
        return_value={"mood_analysed": "happy"}
    )

    result = await service._try_llm_request(
        LLMProvider.OLLAMA,
        "text"
    )

    assert result["mood_analysed"] == "happy"


@pytest.mark.asyncio
async def test_try_llm_request_groq(service):
    service._call_groq = AsyncMock(
        return_value={"mood_analysed": "sad"}
    )

    result = await service._try_llm_request(
        LLMProvider.GROQ,
        "text"
    )

    assert result["mood_analysed"] == "sad"


@pytest.mark.asyncio
async def test_try_llm_request_gemini(service):
    service._call_gemini = AsyncMock(
        return_value={"mood_analysed": "neutral"}
    )

    result = await service._try_llm_request(
        LLMProvider.GEMINI,
        "text"
    )

    assert result["mood_analysed"] == "neutral"


@pytest.mark.asyncio
async def test_try_llm_request_unknown_provider(service):
    result = await service._try_llm_request(
        "INVALID_PROVIDER",
        "text"
    )

    assert result is None


@pytest.mark.asyncio
async def test_try_llm_request_exception(service):
    service._call_ollama = AsyncMock(
        side_effect=Exception("API failure")
    )

    result = await service._try_llm_request(
        LLMProvider.OLLAMA,
        "text"
    )

    assert result is None


# =========================================================
# _parse_llm_response()
# =========================================================

def test_parse_llm_response_valid_json(service):
    response = """
    {
        "mood_analysed": "happy",
        "reason_for_mood": "Positive tone"
    }
    """

    result = service._parse_llm_response(response)

    assert result["mood_analysed"] == "happy"
    assert result["reason_for_mood"] == "Positive tone"


def test_parse_llm_response_markdown_json(service):
    response = """
    ```json
    {
        "mood_analysed": "sad",
        "reason_for_mood": "Negative words"
    }
    ```
    """

    result = service._parse_llm_response(response)

    assert result["mood_analysed"] == "sad"


def test_parse_llm_response_invalid_json(service):
    response = "invalid json"

    result = service._parse_llm_response(response)

    assert result is None


def test_parse_llm_response_missing_fields(service):
    response = """
    {
        "mood_analysed": "happy"
    }
    """

    result = service._parse_llm_response(response)

    assert result is None


def test_parse_llm_response_empty_fields(service):
    response = """
    {
        "mood_analysed": "",
        "reason_for_mood": ""
    }
    """

    result = service._parse_llm_response(response)

    assert result is None


# =========================================================
# _get_default_response()
# =========================================================

def test_get_default_response(service):
    result = service._get_default_response()

    assert result["mood_analysed"] == "neutral"
    assert result["provider_used"] == "default"
    assert result["confidence_score"] == 0.0


# =========================================================
# _is_valid_response()
# =========================================================

def test_is_valid_response_true(service):
    response = {
        "mood_analysed": "happy",
        "reason_for_mood": "positive"
    }

    assert service._is_valid_response(response) is True


def test_is_valid_response_false_missing_fields(service):
    response = {
        "mood_analysed": "happy"
    }

    assert service._is_valid_response(response) is False


def test_is_valid_response_false_empty_values(service):
    response = {
        "mood_analysed": "",
        "reason_for_mood": ""
    }

    assert service._is_valid_response(response) is False