FROM python:3.13-slim
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV PYTHONPATH=/app
EXPOSE 8080
CMD ["python", "app/app.py"]