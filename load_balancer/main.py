import os
import httpx
import asyncio
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv
from prometheus_fastapi_instrumentator import Instrumentator

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

# --- Configuración del Balanceador ---
# Lee la lista de servidores backend desde una variable de entorno
# El formato debe ser una lista de URLs separadas por comas
# Ejemplo: "http://web1:8000,http://web2:8000"
BACKEND_SERVERS_STR = os.getenv("BACKEND_SERVERS", "http://localhost:9001,http://localhost:9002")
BACKEND_SERVERS = [s.strip() for s in BACKEND_SERVERS_STR.split(',')]

# Estado del balanceador
# Usamos un diccionario para poder modificar el índice dentro de las funciones
round_robin_counter = {"index": 0}

# --- Métricas de Prometheus ---
# Expone métricas en el endpoint /metrics
Instrumentator().instrument(app).expose(app)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def reverse_proxy(request: Request, path: str):
    """
    Actúa como un proxy inverso, aplicando balanceo de carga Round-Robin y
    reintentos con backoff exponencial en caso de fallo.
    """
    max_retries = 3
    base_delay = 0.5  # segundos

    for attempt in range(max_retries):
        # --- Lógica de Round-Robin ---
        # Selecciona el próximo servidor de la lista
        server_index = round_robin_counter["index"] % len(BACKEND_SERVERS)
        selected_server = BACKEND_SERVERS[server_index]
        
        # Incrementa el contador para la próxima solicitud
        round_robin_counter["index"] += 1

        # Construye la URL completa del backend
        url = httpx.URL(f"{selected_server}/{path}")
        
        # Lee el cuerpo de la solicitud original
        body = await request.body()
        
        # Crea un cliente HTTP asíncrono
        async with httpx.AsyncClient() as client:
            try:
                print(f"Intento {attempt + 1}: Redirigiendo a {url}")
                
                # Realiza la solicitud al servidor backend, replicando el método, headers y cuerpo
                rp_req = client.build_request(
                    method=request.method,
                    url=url,
                    headers=request.headers.raw,
                    content=body,
                    params=request.query_params,
                )
                
                rp_resp = await client.send(rp_req, timeout=5.0)

                # Si la respuesta es exitosa (ej. 2xx), la devuelve al cliente
                # También consideramos 3xx (redirecciones) y 4xx (errores de cliente) como "exitosos"
                # para que el cliente los maneje. Solo reintentamos en errores de servidor (5xx) o de conexión.
                if rp_resp.status_code < 500:
                    # Devuelve la respuesta del backend tal cual
                    return Response(
                        content=rp_resp.content,
                        status_code=rp_resp.status_code,
                        headers=dict(rp_resp.headers),
                    )
                
                # Si es un error 5xx, se registrará y se reintentará
                print(f"Error 5xx en {url}: {rp_resp.status_code}")

            except httpx.RequestError as e:
                # Error de conexión, timeout, etc.
                print(f"Error de conexión con {url}: {e}")
            
            # --- Lógica de Backoff Exponencial ---
            # Si el intento no fue el último, espera antes de reintentar
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Esperando {delay:.2f}s antes de reintentar...")
                await asyncio.sleep(delay)

    # Si todos los reintentos fallan, devuelve un error 503 Service Unavailable
    return Response(
        content="Todos los servidores backend están inaccesibles.",
        status_code=503,
    )

if __name__ == "__main__":
    import uvicorn
    # Para probar localmente, necesitarías tener los web_app corriendo en puertos diferentes
    # Ejemplo: uvicorn main:app --host 0.0.0.0 --port 80
    uvicorn.run(app, host="0.0.0.0", port=80)
