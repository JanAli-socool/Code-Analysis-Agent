# Code Analysis Agent - Dockerfile with API server
# BUILD_DATE=20240901-7

FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies + build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies system-wide
COPY pro/requirements.txt .
RUN echo "BUILD_DATE=20240901-7" && pip install --no-cache-dir -r requirements.txt

# Install additional tools for analysis
RUN pip install --no-cache-dir \
    cyclonedx-python-lib \
    pip-audit \
    mutmut \
    uvicorn[standard]

# Copy application code
COPY pro/ ./pro/
COPY baseline/ ./baseline/
COPY advanced/ ./advanced/
COPY evaluation/ ./evaluation/
COPY test_repos/ ./test_repos/
COPY CHANGELOG.md README.md AGENT_TRAJECTORIES.md VIDEO_SCRIPT.md ./

# Create non-root user
RUN useradd -m -u 1000 analyzer && \
    chown -R analyzer:analyzer /app
USER analyzer

# Set Python path
ENV PYTHONPATH=/app
ENV PATH=/usr/local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check - check API endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run API server
CMD ["uvicorn", "pro.api.main:app", "--host", "0.0.0.0", "--port", "8000"]