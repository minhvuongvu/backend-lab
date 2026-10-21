# Analysis image for experiment data (pandas + matplotlib), so charts and data work do not depend on
# pip on the host (TLS interception blocks pip on the lab machine; pip inside containers works).
# Build: make analysis-image        Run: make analysis CMD="python scripts/... args"
FROM python:3.13.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
 && python -c "import pandas, matplotlib, numpy; print('pandas', pandas.__version__, 'matplotlib', matplotlib.__version__)"

# The repo is mounted at /lab; commands run relative to it.
WORKDIR /lab
