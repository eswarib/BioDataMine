from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.services.pipelines.dataset_pipeline import get_pipeline
from app.services.pipelines.dataset_pipeline_controller import run_dataset_pipeline
from app.services.pipelines.indexes import ensure_pipeline_indexes
from app.services.pipelines.recovery import requeue_processing_datasets


def create_app() -> FastAPI:
    app = FastAPI(title="DataScan API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.on_event("startup")
    async def _startup():
        p = get_pipeline(runner=run_dataset_pipeline)
        await p.start()
        await ensure_pipeline_indexes()
        # Recover in-flight datasets if the process restarted (in-memory queue is lost).
        await requeue_processing_datasets(p)

    @app.on_event("shutdown")
    async def _shutdown():
        p = get_pipeline(runner=run_dataset_pipeline)
        await p.stop()

    return app


app = create_app()


