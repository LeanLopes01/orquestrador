"""Local-only bridge. Device credentials never leave this Python process."""
import asyncio
import json
import sys
import aiohttp

sys.path.insert(0, r"C:\J.A.R.V.I.S\jarvis\src")
from jarvis_desktop.credentials import Pairing


async def main():
    pairing = Pairing.load()
    if pairing is None:
        return {"status": 503, "body": {"message": "Pareie o Jarvis Desktop neste PC."}}
    if pairing.api_url.rstrip("/") != "https://your-jarvis-api.example.com":
        return {"status": 503, "body": {"message": "O endereço do pareamento não corresponde ao servidor configurado."}}
    data = json.load(sys.stdin)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=85 if '/extension-calls/' in data['path'] else 12)) as http:
        async with http.request(
            data["method"], pairing.api_url.rstrip("/") + data["path"],
            json=data.get("body"), allow_redirects=False,
            headers={"Authorization": f"Bearer {pairing.token}"},
        ) as response:
            body = bytearray()
            async for chunk in response.content.iter_chunked(16384):
                body.extend(chunk)
                if len(body) > 2_000_000:
                    raise ValueError("response too large")
            try:
                result = json.loads(body)
            except json.JSONDecodeError:
                result = {"message": f"Jarvis respondeu HTTP {response.status} fora do formato JSON.", "error": "invalid_upstream_response"}
            return {"status": response.status, "body": result}


try:
    print(json.dumps(asyncio.run(main()), ensure_ascii=False))
except Exception as exc:
    print(json.dumps({"status": 503, "body": {"error": type(exc).__name__, "message": "Não foi possível conectar ao Jarvis. Confira o helper e o servidor."}}))
