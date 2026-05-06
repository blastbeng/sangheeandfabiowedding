FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Find manage.py anywhere and move to root, also find config directory
RUN find . -name "manage.py" -type f -exec mv {} . \; 2>/dev/null || true
RUN find . -type d -name "config" -exec mv {} . \; 2>/dev/null || true
RUN rm -rf backend src project 2>/dev/null || true

# Verify manage.py exists
RUN if [ ! -f manage.py ]; then echo "ERROR: manage.py not found" && exit 1; fi
RUN ls -la /app/

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi"]
