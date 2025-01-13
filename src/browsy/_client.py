from typing import Optional, Dict, Any

import httpx

from browsy._models import Job


class BaseClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _build_url(self, endpoint: str) -> str:
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        return f"{self.base_url}{endpoint}"


class BrowsyClient(BaseClient):
    def __init__(
        self, *, base_url: str, http_client: Optional[httpx.Client] = None
    ) -> None:
        self._http_client = http_client or httpx.Client()
        super().__init__(base_url)

    def create_job(self, name: str, parameters: Dict[str, Any]) -> Job:
        response = self._http_client.post(
            self._build_url("/api/v1/jobs"),
            json={"name": name, "parameters": parameters},
        )
        response.raise_for_status()

        return Job(**response.json())

    def get_job(self, job_id: str) -> Optional[Job]:
        response = self._http_client.get(
            self._build_url(f"/api/v1/jobs/{job_id}")
        )
        if response.status_code >= 400:
            if response.status_code == 404:
                return None
            response.raise_for_status()

        return Job(**response.json())

    def get_job_output(self, job_id: int) -> Optional[bytes]:
        response = self._http_client.get(
            self._build_url(f"/api/v1/jobs/{job_id}/result")
        )
        response.raise_for_status()

        if response.status_code != 200:
            return None

        return response.content


class AsyncBrowsyClient(BaseClient):
    def __init__(
        self, *, base_url: str, http_client: Optional[httpx.AsyncClient] = None
    ) -> None:
        self._http_client = http_client or httpx.AsyncClient()
        super().__init__(base_url)

    async def create_job(self, name: str, parameters: Dict[str, Any]) -> Job:
        response = await self._http_client.post(
            self._build_url("/api/v1/jobs"),
            json={"name": name, "parameters": parameters},
        )
        response.raise_for_status()

        return Job(**response.json())

    async def get_job(self, job_id: str) -> Optional[Job]:
        response = await self._http_client.get(
            self._build_url(f"/api/v1/jobs/{job_id}")
        )
        if response.status_code >= 400:
            if response.status_code == 404:
                return None
            response.raise_for_status()

        return Job(**response.json())

    async def get_job_output(self, job_id: int) -> Optional[bytes]:
        response = await self._http_client.get(
            self._build_url(f"/api/v1/jobs/{job_id}/result")
        )
        response.raise_for_status()

        if response.status_code != 200:
            return None

        return response.content
