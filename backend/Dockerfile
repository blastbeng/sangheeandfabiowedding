FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    libboost-all-dev \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# Compile dlib from source with Raspberry Pi 5 optimizations
ENV CMAKE_ARGS="-DDLIB_USE_NEON=ON -DUSE_NEON=ON -DUSE_AVX=OFF -DCMAKE_BUILD_TYPE=Release"
RUN pip install --no-cache-dir dlib

# Install remaining Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Verify manage.py exists
RUN if [ ! -f manage.py ]; then echo "ERROR: manage.py not found" && exit 1; fi
RUN ls -la /app/

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi"]
