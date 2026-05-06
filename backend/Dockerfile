FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Handle nested Django project structure
RUN if [ ! -f manage.py ] && [ -f backend/manage.py ]; then \
      mv backend/manage.py . && \
      mv backend/config . && \
      rm -rf backend; \
    fi

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi"]
