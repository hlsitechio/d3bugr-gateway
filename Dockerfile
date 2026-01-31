FROM python:3.11-alpine

RUN pip install flask requests gunicorn

WORKDIR /app
COPY server.py .
COPY docs/ ./docs/

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "--timeout", "600", "--workers", "2", "server:app"]
