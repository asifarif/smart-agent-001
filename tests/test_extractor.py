import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock
from core.extractor import extract_admission_info

@pytest.mark.asyncio
async def test_extract_admission_info():
    # Mock Groq API response
    mock_response = {
        "choices": [{
            "message": {
                "content": json.dumps([{
                    "program_name": "BS Computer Science",
                    "category": "undergraduate",
                    "admission_open": True,
                    "application_deadline": "2025-12-31",
                    "link": "https://example.com",
                    "source_text": "BS Computer Science - Admissions Open",
                    "source_url": "https://example.com"
                }])
            }
        }]
    }
    client = AsyncMock()
    client.post = AsyncMock(return_value=MagicMock(json=lambda: mock_response, raise_for_status=lambda: None))
    httpx.AsyncClient = MagicMock(return_value=client)

    result = await extract_admission_info("<html>BS Computer Science</html>", "https://example.com")
    assert len(result) == 1
    assert result[0]["program_name"] == "BS Computer Science"
    assert result[0]["category"] == "undergraduate"