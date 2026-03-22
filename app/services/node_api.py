import httpx
from app.core.config import settings

NODE_API_URL = settings.node_api_url
API_KEY = settings.api_key


async def update_document_status(document_id: str, status: str, error_message: str = None):
    url = f"{NODE_API_URL}/api/v1/documents/{document_id}/status"

    payload = {
        "status": status,
    }

    if error_message:
        payload["errorMessage"] = error_message

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.patch(
            url,
            json=payload,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise Exception(f"Failed to update status: {response.text}")