FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy pyproject.toml and uv.lock to install dependencies
COPY pyproject.toml uv.lock ./

# Install dependencies to system Python
RUN uv pip install --system --no-cache-dir -r pyproject.toml

# Copy application code
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
