from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class AnalyzeRequest(BaseModel):
    repo_path: str
    incremental: bool = False


class AnalyzeResponse(BaseModel):
    job_id: str
    message: str


@router.post("/", response_model=AnalyzeResponse)
async def start_analysis(req: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    engine = request.app.state.engine
    repo_path = Path(req.repo_path).expanduser().resolve()

    if not repo_path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {repo_path}")

    job_id = await engine.analyze_repository(repo_path, incremental=req.incremental)
    return AnalyzeResponse(job_id=job_id, message="Analysis job submitted")


@router.get("/{job_id}/status")
async def get_job_status(job_id: UUID, request: Request):
    engine = request.app.state.engine
    job = engine.scheduler.get_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "error": job.error,
    }
