FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server ./server
COPY agent ./agent
ENV HOMEPULSE_DB=/data/data.db
VOLUME /data
EXPOSE 9090
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "9090"]
