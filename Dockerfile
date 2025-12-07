FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel

# Install CPU PyTorch wheels with versions matching requirements (adjust for GPU builds)
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.9.1 torchvision==0.24.1

RUN pip install --no-cache-dir -r /app/requirements.txt

# copy project
COPY . /app

# create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# entrypoint will run migrations + collectstatic and start gunicorn using $PORT
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "myproject.wsgi:application"]
