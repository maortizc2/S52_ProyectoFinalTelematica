from fastapi import FastAPI, Request, Response, HTTPException
import httpx, os, asyncio, time
from typing import List
from collections import deque

app = FastAPI()

BACKENDS = os.getenv("BACKENDS", "http://web1:5000,http://web2:5000").split(",")
# Use deque for efficient rotation
backend_deque = deque(BACKENDS)
TIMEOUT = float(os.getenv("BACKEND_TIMEOUT", "5.0"))
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", "0.5"))  # base backoff
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Simple health status
health = {b: True for b in BACKENDS}

async def proxy_request(client: httpx.AsyncClient, backend: str, req: Request) -> httpx.Response:
    url = backend + req.url.path
    if req.url.query:
        url += "?" + req.url.query
    headers = dict(req.headers)
    try:
        content = await req.body()
    except Exception:
        content = None
    resp = await client.request(method=req.method, url=url, headers=headers, content=content, timeout=TIMEOUT)
    return resp

@app.middleware("http")
async def round_robin_proxy(request: Request, call_next):
    # pick next backend
    tries = 0
    last_exc = None
    async with httpx.AsyncClient() as client:
        for i in range(len(backend_deque)):
            backend = backend_deque[0]  # peek
            backend_deque.rotate(-1)    # advance for next request (round-robin)
            if not health.get(backend, True):
                continue
            # try up to MAX_RETRIES with backoff
            for attempt in range(1, MAX_RETRIES+1):
                try:
                    resp = await proxy_request(client, backend, request)
                    # if server returns 5xx treat as error and retry
                    if resp.status_code >= 500:
                        raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
                    # success: return response to client
                    headers = dict(resp.headers)
                    content = resp.content
                    return Response(content=content, status_code=resp.status_code, headers=headers)
                except Exception as e:
                    last_exc = e
                    await asyncio.sleep(RETRY_BACKOFF * attempt)
                    continue
        # If we reached here, no backends succeeded
        raise HTTPException(status_code=502, detail="Bad gateway: all backends failed")

@app.get("/metrics")
def metrics():
    return {"backends": BACKENDS, "health": health}

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
