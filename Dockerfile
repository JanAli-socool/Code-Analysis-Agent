# Code Analysis Agent - Single-stage Dockerfile (forces fresh install)
# BUILD_DATE=20240901-6

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
RUN echo "BUILD_DATE=20240901-6" && pip install --no-cache-dir -r requirements.txt

# Install additional tools for analysis
RUN pip install --no-cache-dir \
    cyclonedx-python-lib \
    pip-audit \
    mutmut

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

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -m pro.cli --version || exit 1

# Default command
ENTRYPOINT ["python", "-m", "pro.cli"]
CMD ["--help"]