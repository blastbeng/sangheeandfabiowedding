FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Verify manage.py exists
RUN if [ ! -f manage.py ]; then echo "ERROR: manage.py not found" && exit 1; fi
RUN ls -la /app/

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi"]
