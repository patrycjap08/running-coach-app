"""Small GitHub Contents/Data API adapter for the private training repository."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from .config import Settings


class DataStoreError(RuntimeError):
    """A safe-to-display error from the private GitHub data repository."""


class GitHubDataStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = "https://api.github.com"

    @property
    def configured(self) -> bool:
        return bool(self.settings.github_data_token and self.settings.github_data_repo)

    def _headers(self) -> dict[str, str]:
        token = self.settings.github_data_token
        if not token:
            raise DataStoreError("Repozytorium danych nie jest jeszcze skonfigurowane.")
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/repos/{self.settings.github_data_repo}/{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = httpx.request(method, self._url(path), headers=self._headers(), timeout=30, **kwargs)
        except httpx.HTTPError as exc:
            raise DataStoreError("Nie udało się połączyć z prywatnym repozytorium danych.") from exc
        if response.status_code >= 400:
            if response.status_code in (401, 403):
                message = "Token GitHub nie ma dostępu do prywatnego repozytorium danych."
            elif response.status_code == 404:
                message = "Nie znaleziono prywatnego repozytorium danych."
            elif response.status_code == 409:
                message = "Repozytorium danych zmieniło się w tym samym czasie. Spróbuj ponownie."
            else:
                message = "GitHub chwilowo odrzucił operację na repozytorium danych."
            raise DataStoreError(message)
        return response

    def read_json(self, path: str, default: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "GET",
            f"contents/{path}",
            params={"ref": self.settings.github_data_branch},
        )
        try:
            encoded = response.json()["content"]
            return json.loads(base64.b64decode(encoded).decode("utf-8"))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DataStoreError(f"Plik {path} w repozytorium danych ma niepoprawny format.") from exc

    def read_text(self, path: str) -> str:
        response = self._request(
            "GET",
            f"contents/{path}",
            params={"ref": self.settings.github_data_branch},
        )
        try:
            encoded = response.json()["content"]
            return base64.b64decode(encoded).decode("utf-8")
        except (KeyError, TypeError, ValueError) as exc:
            raise DataStoreError(f"Plik {path} w repozytorium danych jest nieczytelny.") from exc

    def read_text_optional(self, path: str) -> str | None:
        try:
            return self.read_text(path)
        except DataStoreError as exc:
            if str(exc) == "Nie znaleziono prywatnego repozytorium danych.":
                return None
            raise

    def commit_files(self, files: dict[str, str], message: str) -> str | None:
        """Commit several files in one Git Data API commit."""

        if not files:
            return None

        reference = self._request(
            "GET",
            f"git/ref/heads/{self.settings.github_data_branch}",
        ).json()
        head_sha = reference["object"]["sha"]
        base_tree_sha = self._request("GET", f"git/commits/{head_sha}").json()["tree"]["sha"]

        tree_entries: list[dict[str, str]] = []
        for path, content in files.items():
            blob_sha = self._request(
                "POST",
                "git/blobs",
                json={
                    "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                    "encoding": "base64",
                },
            ).json()["sha"]
            tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob_sha})

        tree_sha = self._request(
            "POST",
            "git/trees",
            json={"base_tree": base_tree_sha, "tree": tree_entries},
        ).json()["sha"]
        commit_sha = self._request(
            "POST",
            "git/commits",
            json={"message": message, "tree": tree_sha, "parents": [head_sha]},
        ).json()["sha"]
        self._request(
            "PATCH",
            f"git/refs/heads/{self.settings.github_data_branch}",
            json={"sha": commit_sha, "force": False},
        )
        return commit_sha
