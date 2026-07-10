import asyncio

MYDRAMALIST_WEBSITE = "https://mydramalist.com/"  # MyDramaList.com

# Max concurrent outbound requests to MDL per Kuryana process.
# With 2 instances behind nginx: 2 × 3 = 6 simultaneous MDL requests.
MDL_SEMAPHORE = asyncio.Semaphore(3)

# Camoufox (headless Firefox) uses ~500 MB each — allow only 1 per process.
CAMOUFOX_SEMAPHORE = asyncio.Semaphore(1)


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", reload=True)
