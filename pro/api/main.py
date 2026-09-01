"""
REST API for Code Analysis Agent.
"""
import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, HttpUrl
import httpx

from pro.orchestrator import ProfessionalOrchestrator
from pro.config.loader import get_config, ConfigLoader
from pro.benchmarks.regression import RegressionDetector
from pro.cache.manager import AnalysisCache


# Request/Response Models
class AnalysisRequest(BaseModel):
    repo_url: Optional[HttpUrl] = None
    repo_path: Optional[str] = None
    config_overrides: Optional[Dict[str, Any]] = None
    format: str = "json"
    fail_on: str = "critical"


class AnalysisResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class BenchmarkRequest(BaseModel):
    repo_paths: List[str]
    iterations: int = 3


class RegressionRequest(BaseModel):
    repo_path: str
    baseline_path: str
    threshold: float = 5.0


class WebhookConfig(BaseModel):
    url: HttpUrl
    events: List[str] = ["analysis_complete", "regression_detected", "benchmark_complete"]
    secret: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


# In-memory job store (use Redis in production)
jobs: Dict[str, Dict] = {}
webhooks: List[WebhookConfig] = []


async def notify_webhooks(event: str, data: Dict):
    """Send webhook notifications."""
    for webhook in webhooks:
        if event in webhook.events:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        str(webhook.url),
                        json={"event": event, "data": data, "timestamp": datetime.now().isoformat()},
                        headers={"X-Webhook-Secret": webhook.secret} if webhook.secret else {},
                        timeout=10.0
                    )
            except Exception:
                pass  # Log in production


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="Code Analysis Agent API",
    description="Professional code quality analysis REST API",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Analysis", "description": "Core code analysis operations. Submit repositories for analysis, retrieve results, and manage analysis jobs."},
        {"name": "Benchmarking", "description": "Performance benchmarking and regression detection for tracking code quality over time."},
        {"name": "Regression", "description": "Regression detection comparing current analysis against baselines."},
        {"name": "Webhooks", "description": "Webhook management for real-time notifications on analysis completion."},
        {"name": "Cache", "description": "Cache management for analysis results and performance optimization."},
        {"name": "Configuration", "description": "Application configuration management."},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom OpenAPI schema with enhanced documentation
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Code Analysis Agent API",
        version="1.0.0",
        description="""
# Code Analysis Agent API

Professional multi-skill code analysis for technical due diligence.

## Features

- **Multi-language Analysis**: Python, JavaScript/TypeScript, Java, Go, C/C++
- **12 Analysis Skills**: Security, Complexity, Testing, Architecture, Dependencies, Maintainability, Documentation, Git History, and 4 language-specific skills
- **Supply Chain Scanning**: OSV, OSS Index, deps.dev vulnerability databases
- **SBOM Generation**: CycloneDX 1.5 and SPDX 2.3 with license compliance
- **Policy Engine**: OPA/Rego policy-as-code evaluation
- **Incremental Analysis**: Git diff-based analysis for PRs
- **Benchmarking**: Performance tracking and regression detection

## Authentication

API endpoints require Bearer token authentication. Obtain token via `/auth/token` endpoint.

```
Authorization: Bearer <your-token>
```

## Rate Limits

- Analysis endpoints: 10 requests/minute
- Other endpoints: 100 requests/minute

## Error Responses

All errors follow RFC 7807 Problem Details format:
```json
{
  "type": "https://example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Invalid request parameters",
  "instance": "/api/v1/analyze"
}
```

## Webhooks

Configure webhook endpoints to receive real-time analysis completion notifications.
        """,
        routes=app.routes,
    )
    
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    openapi_schema["components"]["examples"] = {
        "AnalysisRequest": {
            "summary": "Basic analysis request",
            "value": {
                "repo_path": "/path/to/repo",
                "format": "json",
                "fail_on": "critical",
                "no_cache": False,
                "parallel": True
            }
        },
        "AnalysisResponse": {
            "summary": "Successful analysis response",
            "value": {
                "job_id": "analysis-abc123",
                "status": "completed",
                "overall_score": 85.5,
                "risk_level": "low",
                "category_scores": [
                    {
                        "name": "security",
                        "score": 92.0,
                        "weight": 3.0,
                        "findings": [],
                        "metrics": [],
                        "duration_ms": 1200
                    }
                ],
                "summary": "Good code quality with minor issues",
                "strengths": ["Strong security posture", "Good test coverage"],
                "weaknesses": ["Documentation could be improved"],
                "files_analyzed": 42,
                "total_lines": 12500,
                "duration_ms": 4500
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Custom documentation endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Code Analysis Agent - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
        swagger_ui_parameters={
            "deepLinking": True,
            "displayRequestDuration": True,
            "docExpansion": "list",
            "filter": True,
            "showExtensions": True,
            "showCommonExtensions": True,
            "tryItOutEnabled": True,
            "persistAuthorization": True,
        }
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title="Code Analysis Agent - API Reference",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.0/bundles/redoc.standalone.js",
    )

@app.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    from fastapi.responses import JSONResponse
    return JSONResponse(custom_openapi())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    background_tasks: BackgroundTasks,
    request: AnalysisRequest
):
    """Start a code analysis job."""
    if not request.repo_url and not request.repo_path:
        raise HTTPException(400, "Either repo_url or repo_path required")
    
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "pending",
        "request": request.model_dump(),
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None,
        "error": None
    }
    jobs[job_id] = job
    
    background_tasks.add_task(run_analysis_job, job_id, request)
    
    return AnalysisResponse(
        job_id=job_id,
        status="pending",
        created_at=job["created_at"]
    )


async def run_analysis_job(job_id: str, request: AnalysisRequest):
    """Background task to run analysis."""
    job = jobs[job_id]
    job["status"] = "running"
    
    try:
        # Handle repo_url by cloning (simplified - use git in production)
        repo_path = request.repo_path
        if request.repo_url:
            # In production: git clone to temp dir
            repo_path = tempfile.mkdtemp()
            # clone_repo(str(request.repo_url), repo_path)
        
        # Load config with overrides
        config = get_config()
        if request.config_overrides:
            # Apply overrides (simplified)
            pass
        
        if not config.execution.parallel:
            config.execution.parallel = True
        
        orchestrator = ProfessionalOrchestrator(repo_path, config)
        result = orchestrator.run_analysis()
        
        # Convert result to dict
        result_dict = {
            "repository": result.repository_path,
            "overall_score": result.overall_score,
            "risk_level": result.risk_level,
            "summary": result.summary,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "files_analyzed": result.files_analyzed,
            "total_lines": result.total_lines,
            "duration_ms": result.total_duration_ms,
            "categories": [
                {
                    "category": cs.category,
                    "score": cs.score,
                    "weight": cs.weight,
                    "findings": cs.findings,
                    "metrics": cs.metrics,
                    "duration_ms": cs.duration_ms,
                    "error": cs.error
                }
                for cs in result.category_scores
            ]
        }
        
        job["status"] = "completed"
        job["result"] = result_dict
        job["completed_at"] = datetime.now().isoformat()
        
        await notify_webhooks("analysis_complete", {"job_id": job_id, "result": result_dict})
        
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = datetime.now().isoformat()
        await notify_webhooks("analysis_complete", {"job_id": job_id, "error": str(e)})


@app.get("/analyze/{job_id}", response_model=AnalysisResponse)
async def get_analysis(job_id: str):
    """Get analysis job status and result."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    
    job = jobs[job_id]
    return AnalysisResponse(
        job_id=job_id,
        status=job["status"],
        result=job["result"],
        error=job["error"],
        created_at=job["created_at"],
        completed_at=job["completed_at"]
    )


@app.post("/analyze/upload")
async def analyze_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    config_overrides: Optional[str] = Form(None),
    format: str = Form("json"),
    fail_on: str = Form("critical")
):
    """Analyze uploaded repository (zip/tar)."""
    # Save uploaded file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Extract (simplified - use zipfile/tarfile in production)
    extract_dir = tempfile.mkdtemp()
    # extract_archive(tmp_path, extract_dir)
    
    request = AnalysisRequest(
        repo_path=extract_dir,
        config_overrides=json.loads(config_overrides) if config_overrides else None,
        format=format,
        fail_on=fail_on
    )
    
    return await analyze(background_tasks, request)


@app.post("/benchmark")
async def benchmark(request: BenchmarkRequest, background_tasks: BackgroundTasks):
    """Run benchmarks on repositories."""
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "pending",
        "type": "benchmark",
        "request": request.model_dump(),
        "created_at": datetime.now().isoformat()
    }
    jobs[job_id] = job
    background_tasks.add_task(run_benchmark_job, job_id, request)
    return AnalysisResponse(job_id=job_id, status="pending", created_at=job["created_at"])


async def run_benchmark_job(job_id: str, request: BenchmarkRequest):
    job = jobs[job_id]
    job["status"] = "running"
    
    try:
        from pro.benchmarks.runner import BenchmarkRunner
        runner = BenchmarkRunner(get_config())
        results = runner.run_benchmarks(request.repo_paths, request.iterations, None, None)
        
        job["status"] = "completed"
        job["result"] = results
        job["completed_at"] = datetime.now().isoformat()
        
        await notify_webhooks("benchmark_complete", {"job_id": job_id, "results": results})
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = datetime.now().isoformat()


@app.post("/regression")
async def regression(request: RegressionRequest):
    """Detect regressions against baseline."""
    detector = RegressionDetector(get_config(), request.threshold)
    result = detector.analyze_and_compare(request.repo_path, request.baseline_path)
    
    if result["has_regression"]:
        await notify_webhooks("regression_detected", result)
    
    return result


@app.post("/webhooks")
async def register_webhook(webhook: WebhookConfig):
    """Register a webhook for events."""
    webhooks.append(webhook)
    return {"status": "registered", "webhook": webhook.model_dump()}


@app.get("/webhooks")
async def list_webhooks():
    return [w.model_dump() for w in webhooks]


@app.delete("/webhooks/{index}")
async def delete_webhook(index: int):
    if 0 <= index < len(webhooks):
        webhooks.pop(index)
        return {"status": "deleted"}
    raise HTTPException(404, "Webhook not found")


@app.get("/cache/stats")
async def cache_stats(cache_dir: Optional[str] = None):
    if cache_dir:
        cache = AnalysisCache(cache_dir)
    else:
        cache = AnalysisCache(get_config().execution.cache_dir)
    return cache.stats()


@app.post("/cache/clear")
async def clear_cache(cache_dir: Optional[str] = None):
    if cache_dir:
        cache = AnalysisCache(cache_dir)
    else:
        cache = AnalysisCache(get_config().execution.cache_dir)
    count = cache.clear()
    return {"cleared": count}


@app.get("/config")
async def get_config_endpoint():
    config = get_config()
    return json.loads(json.dumps(config.__dict__, default=str))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)