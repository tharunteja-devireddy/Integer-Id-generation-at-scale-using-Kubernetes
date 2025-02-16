FROM python:3.11-slim

WORKDIR /app
COPY .. /app

RUN pip install -r requirements.txt

RUN python3 -m pip uninstall pip

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
