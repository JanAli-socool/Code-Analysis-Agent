"""
OpenAPI Documentation with Swagger UI for Code Analysis Agent API.
"""
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

# This would be integrated into pro/api/main.py
# Adding custom OpenAPI schema and Swagger UI configuration

def custom_openapi(app: FastAPI):
    """Generate custom OpenAPI schema with detailed documentation."""
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
    
    # Add custom components
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
    
    # Add custom examples
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


def setup_docs(app: FastAPI):
    """Setup custom documentation endpoints."""
    
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
        return JSONResponse(custom_openapi(app))


# Custom OpenAPI tags metadata
TAGS_METADATA = [
    {
        "name": "Analysis",
        "description": "Core code analysis operations. Submit repositories for analysis, retrieve results, and manage analysis jobs.",
    },
    {
        "name": "Benchmarking",
        "description": "Performance benchmarking and regression detection for tracking code quality over time.",
    },
    {
        "name": "Regression",
        "description": "Regression detection comparing current analysis against baselines.",
    },
    {
        "name": "Webhooks",
        "description": "Webhook management for real-time notifications on analysis completion.",
    },
    {
        "name": "Cache",
        "description": "Cache management for analysis results and performance optimization.",
    },
    {
        "name": "Configuration",
        "description": "Application configuration management.",
    },
]

# Extended API schema with detailed descriptions
EXTENDED_SCHEMA = {
    "AnalysisRequest": {
        "type": "object",
        "properties": {
            "repo_path": {
                "type": "string",
                "description": "Path to the repository to analyze (local path or Git URL)",
                "example": "/home/user/my-project"
            },
            "format": {
                "type": "string",
                "enum": ["json", "sarif", "html", "markdown"],
                "default": "json",
                "description": "Output format for the analysis report"
            },
            "fail_on": {
                "type": "string",
                "enum": ["critical", "high", "medium", "low", "none"],
                "default": "critical",
                "description": "Risk level threshold to fail the analysis"
            },
            "no_cache": {
                "type": "boolean",
                "default": False,
                "description": "Disable cache and force fresh analysis"
            },
            "parallel": {
                "type": "boolean",
                "default": True,
                "description": "Enable parallel skill execution"
            },
            "config": {
                "type": "object",
                "description": "Optional configuration overrides for this analysis",
                "properties": {
                    "weights": {
                        "type": "object",
                        "description": "Custom skill weights override",
                        "example": {"security": 5.0, "testing": 3.0}
                    },
                    "thresholds": {
                        "type": "object",
                        "description": "Custom thresholds override",
                        "example": {"max_complexity": 10, "min_test_coverage": 90}
                    }
                }
            }
        },
        "required": ["repo_path"]
    },
    "AnalysisResponse": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Unique analysis job identifier"},
            "status": {"type": "string", "enum": ["queued", "running", "completed", "failed"]},
            "result": {
                "type": "object",
                "properties": {
                    "overall_score": {"type": "number", "format": "float"},
                    "risk_level": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "category_scores": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "score": {"type": "number"},
                                "weight": {"type": "number"},
                                "findings": {"type": "array", "items": {"type": "object"}},
                                "metrics": {"type": "array", "items": {"type": "object"}},
                                "duration_ms": {"type": "number"}
                            }
                        }
                    },
                    "summary": {"type": "string"},
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "weaknesses": {"type": "array", "items": {"type": "string"}},
                    "files_analyzed": {"type": "integer"},
                    "total_lines": {"type": "integer"},
                    "duration_ms": {"type": "number"}
                }
            },
            "error": {"type": "string", "nullable": True},
            "created_at": {"type": "string", "format": "date-time"},
            "completed_at": {"type": "string", "format": "date-time", "nullable": True}
        }
    },
    "SBOMRequest": {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Repository path"},
            "format": {"type": "string", "enum": ["cyclonedx-json", "spdx-json"], "default": "cyclonedx-json"},
            "sign": {"type": "boolean", "default": False, "description": "Sign the SBOM with Cosign"},
            "signing_mode": {"type": "string", "enum": ["keyless", "key"], "default": "keyless"}
        },
        "required": ["repo_path"]
    },
    "PolicyEvaluationRequest": {
        "type": "object",
        "properties": {
            "analysis_result": {"type": "object", "description": "Full analysis result object"},
            "policy_ids": {"type": "array", "items": {"type": "string"}, "description": "Optional specific policies to evaluate"}
        },
        "required": ["analysis_result"]
    },
    "BenchmarkRequest": {
        "type": "object",
        "properties": {
            "repo_paths": {"type": "array", "items": {"type": "string"}, "description": "Paths to repositories to benchmark"},
            "iterations": {"type": "integer", "default": 3, "description": "Number of iterations per repository"},
            "baseline_path": {"type": "string", "description": "Optional baseline results file for comparison"}
        },
        "required": ["repo_paths"]
    },
    "RegressionRequest": {
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Repository path"},
            "baseline_path": {"type": "string", "description": "Baseline results file path"},
            "threshold": {"type": "number", "default": 5.0, "description": "Score change threshold for regression detection"}
        },
        "required": ["repo_path", "baseline_path"]
    }
}