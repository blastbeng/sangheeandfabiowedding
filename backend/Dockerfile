FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    libboost-all-dev \
    libopenblas-dev \
    liblapack-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# Copy the prebuilt dlib wheel from the build context
COPY build/dlib-*.whl /tmp/dlib/

# Install the prebuilt dlib wheel
RUN pip install --no-cache-dir /tmp/dlib/dlib-*.whl

# Install remaining Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Verify manage.py exists
RUN if [ ! -f manage.py ]; then echo "ERROR: manage.py not found" && exit 1; fi
RUN ls -la /app/

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi"]
