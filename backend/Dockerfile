FROM python:3.10

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of backend files
COPY . . 

# install spatial for duckdb
RUN python -c "import duckdb; conn=duckdb.connect(); conn.execute('INSTALL spatial');"

# Expose FastAPI port
EXPOSE 8000

# Run the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]