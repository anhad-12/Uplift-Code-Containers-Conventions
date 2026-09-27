FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt uvicorn==0.30.6
COPY shop/ ./shop/
CMD ["python", "-m", "uvicorn", "shop.app:app", "--host", "0.0.0.0", "--port", "8000"]
