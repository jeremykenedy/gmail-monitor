FROM python:3.12-alpine

WORKDIR /app

RUN pip install --no-cache-dir schedule

COPY src/ ./src/

ENV TZ=America/Los_Angeles

CMD ["python", "src/scheduler.py"]
