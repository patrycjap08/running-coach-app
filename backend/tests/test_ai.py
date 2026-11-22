import json

import pytest

from app.ai import AIAnalysisError, OpenAIAnalyzer
from app.config import Settings


def test_openai_analyzer_requires_key() -> None:
    analyzer = OpenAIAnalyzer(Settings(openai_api_key=None))
    with pytest.raises(AIAnalysisError, match="OPENAI_API_KEY"):
        analyzer.analyze_activity({"activity_id": "1"}, [])


def test_openai_analyzer_reads_structured_response() -> None:
    result = {
        "summary": "Równy bieg.",
        "classification": "easy",
        "confidence": "medium",
        "positives": ["Równe tempo"],
        "risks": [],
        "recommendation": "planned",
        "recommendation_text": "Kontynuuj plan.",
        "plan_alignment": "not_assessed",
        "uncertainty": ["Brak opisu planu"],
    }
    parsed = OpenAIAnalyzer._parse_response({"status": "completed", "output_text": json.dumps(result)})
    assert parsed == result


def test_openai_analyzer_rejects_incomplete_response() -> None:
    with pytest.raises(AIAnalysisError, match="niekompletna"):
        OpenAIAnalyzer._parse_response({"status": "incomplete"})
