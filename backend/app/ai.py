"""Structured, privacy-aware activity analysis through the OpenAI Responses API."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from .config import Settings


ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "classification": {
            "type": "string",
            "enum": ["easy", "long", "tempo", "intervals", "race", "other", "unknown"],
        },
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "positives": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "recommendation": {
            "type": "string",
            "enum": ["rest", "easy", "planned", "quality", "unknown"],
        },
        "recommendation_text": {"type": "string"},
        "plan_alignment": {"type": "string", "enum": ["assessed", "not_assessed"]},
        "uncertainty": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "summary",
        "classification",
        "confidence",
        "positives",
        "risks",
        "recommendation",
        "recommendation_text",
        "plan_alignment",
        "uncertainty",
    ],
    "additionalProperties": False,
}


class AIAnalysisError(RuntimeError):
    """A safe-to-display AI analysis error."""


class OpenAIAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.openai_api_key and self.settings.openai_api_key.strip())

    def analyze_activity(self, activity: dict[str, str], context: list[dict[str, str]]) -> dict[str, Any]:
        if not self.configured:
            raise AIAnalysisError("OPENAI_API_KEY nie jest skonfigurowany.")

        prompt = json.dumps(
            {"activity": activity, "previous_activities": context},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        payload = {
            "model": self.settings.openai_model or "gpt-4o-mini",
            "store": False,
            "instructions": (
                "Jesteś ostrożnym trenerem biegania. Odpowiadaj po polsku. "
                "Interpretuj tylko podane dane, nie diagnozuj i nie wymyślaj brakujących pomiarów. "
                "Nie oceniaj zgodności z planem, jeśli planu nie ma. Zwróć wyłącznie dane zgodne ze schematem."
            ),
            "input": (
                "Przeanalizuj pojedynczą aktywność na tle wcześniejszych aktywności. "
                "Puste pola oznaczają brak danych, a nie zero. Podaj krótkie, konkretne wnioski.\n"
                + prompt
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "running_activity_analysis",
                    "strict": True,
                    "schema": ANALYSIS_SCHEMA,
                }
            },
            "max_output_tokens": self.settings.ai_max_output_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key.strip()}",
            "Content-Type": "application/json",
        }

        for attempt in range(3):
            try:
                response = httpx.post(
                    "https://api.openai.com/v1/responses",
                    headers=headers,
                    json=payload,
                    timeout=90,
                )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise AIAnalysisError("Nie udało się połączyć z OpenAI.") from exc
                time.sleep(2**attempt)
                continue

            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                retry_after = response.headers.get("retry-after")
                try:
                    delay = min(float(retry_after), 10) if retry_after else 2**attempt
                except ValueError:
                    delay = 2**attempt
                time.sleep(delay)
                continue
            if response.status_code >= 400:
                if response.status_code in (401, 403):
                    message = "OpenAI odrzuciło klucz API albo konto nie ma dostępu do modelu."
                elif response.status_code == 429:
                    message = "OpenAI chwilowo ograniczyło liczbę żądań lub limit wydatków."
                else:
                    message = "OpenAI zwróciło błąd podczas analizy."
                raise AIAnalysisError(message)
            return self._parse_response(response.json())

        raise AIAnalysisError("OpenAI chwilowo nie odpowiada. Analiza pozostaje oczekująca.")

    @staticmethod
    def _parse_response(body: dict[str, Any]) -> dict[str, Any]:
        if body.get("status") == "incomplete" or body.get("incomplete_details"):
            raise AIAnalysisError("Odpowiedź OpenAI była niekompletna. Analiza pozostaje oczekująca.")
        if body.get("error"):
            raise AIAnalysisError("OpenAI nie zwróciło kompletnej analizy.")

        output_text = body.get("output_text")
        if not isinstance(output_text, str):
            chunks: list[str] = []
            for item in body.get("output", []):
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []):
                    if isinstance(content, dict) and isinstance(content.get("text"), str):
                        chunks.append(content["text"])
            output_text = "".join(chunks)
        try:
            result = json.loads(output_text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise AIAnalysisError("OpenAI zwróciło odpowiedź poza oczekiwanym formatem.") from exc
        if not isinstance(result, dict) or not all(key in result for key in ANALYSIS_SCHEMA["required"]):
            raise AIAnalysisError("OpenAI zwróciło niepełną analizę.")
        return result
