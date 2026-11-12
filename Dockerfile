
FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libglib2.0-dev \
    curl \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Deno JavaScript Runtime
ENV DENO_INSTALL="/root/.deno"

RUN curl -fsSL https://deno.land/install.sh | sh

ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Verify Deno installation
RUN deno --version

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.enableCORS", "false", "--server.port", "8501"]
