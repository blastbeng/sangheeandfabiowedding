FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    libboost-all-dev \
    libopenblas-dev \
    liblapack-dev \
    libgl1 \
    libglib2.0-0 \
    wget \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Build latest stable dlib from source with RPi5 optimizations (NEON, BLAS, LAPACK)
# Use 4 parallel build jobs
RUN CMAKE_ARGS="-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DDLIB_NO_GUI_SUPPORT=ON -DUSE_NEON=ON -DUSE_AVX=OFF -DUSE_SSE2=OFF -DUSE_SSE4=OFF -DUSE_AVX2=OFF -DDLIB_USE_BLAS=ON -DDLIB_USE_LAPACK=ON" \
    CMAKE_BUILD_PARALLEL_LEVEL=4 \
    pip install --no-cache-dir --no-binary dlib dlib

COPY requirements.txt .

# Install remaining Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Verify that both dlib models are accessible
RUN python -c "\
import face_recognition_models; \
import dlib; \
predictor = dlib.shape_predictor(face_recognition_models.pose_predictor_model_location()); \
recognizer = dlib.face_recognition_model_v1(face_recognition_models.face_recognition_model_location()); \
print('Face recognition models verified OK')"

COPY download_models.sh /usr/local/bin/download_models.sh
RUN chmod +x /usr/local/bin/download_models.sh

COPY . .

# Verify manage.py exists
RUN if [ ! -f manage.py ]; then echo "ERROR: manage.py not found" && exit 1; fi
RUN ls -la /app/

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi"]
