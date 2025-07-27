FROM python:3.13-slim
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
WORKDIR /app
COPY . /app
EXPOSE 8080
CMD ["python", "app.py"]