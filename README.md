# Running Coach

Prywatna aplikacja webowa do analizy treningów z Garmin Connect. Frontend działa w React + TypeScript + Vite, a backend w FastAPI. Aktualny commit zawiera pierwszy fundament projektu: interfejs zgodny z makietą, tryb demo, bezpieczny szkielet konfiguracji i chroniony endpoint API.

## Repozytoria

- `running-coach-app` — kod aplikacji, frontend, backend i deployment.
- `running-coach-data` — prywatne dane treningowe przechowywane osobno.

## Uruchomienie frontendu

```bash
npm install
npm run dev
```

Frontend startuje w trybie demo. Nie zawiera kluczy Garmin, OpenAI ani GitHub.

## Uruchomienie backendu

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Skopiuj `.env.example` do `.env` tylko lokalnie. Plik `.env` jest ignorowany przez Git. Klucz Garmin będzie dodany dopiero jako zmienna środowiskowa usługi backendu na Renderze:

```env
GARMIN_PERSONAL_API_KEY=...
```

Nie wpisuj tego klucza do kodu, frontendu, GitHub Pages ani repozytorium danych.

## Testy backendu

```bash
cd backend
pytest
```

## GitHub Pages i Render

Workflow `pages.yml` buduje frontend i publikuje wyłącznie katalog `dist`. Włącz GitHub Pages w ustawieniach repozytorium, wybierając publikowanie przez GitHub Actions.

Plik `render.yaml` opisuje usługę FastAPI. Po utworzeniu Web Service na Renderze uzupełnij w zakładce **Environment** sekrety oznaczone jako `sync: false`, w szczególności `GARMIN_PERSONAL_API_KEY`. Sekrety nie są wpisywane do tego repozytorium.

## Następne etapy

1. Dodać adapter Garmin Personal API i synchronizację przyrostową.
2. Dodać GitHub Data API dla prywatnego repozytorium danych.
3. Dodać analizę OpenAI Structured Outputs.
4. Wdrożyć backend na Renderze i dopiero wtedy skonfigurować `GARMIN_PERSONAL_API_KEY`.
