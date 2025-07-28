FROM python:3.13-slim
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN mkdir -p /app
COPY . /app
WORKDIR /app
EXPOSE 8080
CMD ["python", "./app/app.py"]