import uuid

from app.application.validation.schema_validator import validate_agent_result


def _valid_raw(task_id: uuid.UUID) -> dict:
    return {
        "task_id": str(task_id),
        "agent_name": "TechnicalSEOAgent",
        "status": "completed",
        "findings": [
            {
                "category": "crawlability",
                "severity": "high",
                "title": "robots.txt blocks /products",
                "description": "desc",
                "evidence": "robots.txt line 3",
                "recommendation": "fix it",
            }
        ],
        "confidence": 0.9,
        "limitations": [],
        "follow_up_suggestions": [],
    }


def test_validate_agent_result_accepts_well_formed_dict():
    task_id = uuid.uuid4()
    result = validate_agent_result(_valid_raw(task_id))
    assert result is not None
    assert result.task_id == task_id
    assert len(result.findings) == 1


def test_validate_agent_result_rejects_missing_required_field():
    raw = _valid_raw(uuid.uuid4())
    del raw["confidence"]
    assert validate_agent_result(raw) is None


def test_validate_agent_result_rejects_invalid_severity_literal():
    raw = _valid_raw(uuid.uuid4())
    raw["findings"][0]["severity"] = "catastrophic"  # not a valid Literal value
    assert validate_agent_result(raw) is None


def test_validate_agent_result_rejects_malformed_uuid():
    raw = _valid_raw(uuid.uuid4())
    raw["task_id"] = "not-a-uuid"
    assert validate_agent_result(raw) is None


def test_validate_agent_result_round_trips_references_confidence_and_model():
    raw = _valid_raw(uuid.uuid4())
    raw["model"] = "qwen-plus"
    raw["findings"][0]["references"] = ["https://developers.google.com/search/docs/crawling-indexing/robots-txt"]
    raw["findings"][0]["confidence"] = 0.85

    result = validate_agent_result(raw)

    assert result is not None
    assert result.model == "qwen-plus"
    assert result.findings[0].references == [
        "https://developers.google.com/search/docs/crawling-indexing/robots-txt"
    ]
    assert result.findings[0].confidence == 0.85


def test_validate_agent_result_defaults_references_and_confidence_when_absent():
    result = validate_agent_result(_valid_raw(uuid.uuid4()))

    assert result is not None
    assert result.model is None
    assert result.findings[0].references == []
    assert result.findings[0].confidence is None
