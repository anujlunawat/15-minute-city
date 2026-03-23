FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y locales && \
    locale-gen en_US.UTF-8 && \
    update-locale LANG=en_US.UTF-8

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Base dependencies
RUN apt update && apt install -y \
    curl \
    git \
    gnupg \
    build-essential \
    ca-certificates \
    lsb-release \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# Install Node 20 LTS
# -------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt update && apt install -y nodejs

# -------------------------
# Install MongoDB (Official Repo)
# -------------------------
RUN curl -fsSL https://pgp.mongodb.com/server-7.0.asc | \
    gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg

RUN echo "deb [ arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
    https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" \
    | tee /etc/apt/sources.list.d/mongodb-org-7.0.list

RUN apt update && apt install -y mongodb-org

# -------------------------
# Install Redis (Official Source)
# -------------------------
RUN wget http://download.redis.io/redis-stable.tar.gz && \
    tar xzf redis-stable.tar.gz && \
    cd redis-stable && \
    make && make install && \
    cd .. && rm -rf redis-stable redis-stable.tar.gz

WORKDIR /workspace

# Backend dependencies
# COPY backend/requirements.txt backend/requirements.txt
# RUN pip3 install --no-cache-dir -r backend/requirements.txt

# # Frontend dependencies
# COPY frontend/package*.json frontend/
# RUN cd frontend && npm install

# EXPOSE 3000 8000 6379 27017

CMD ["bash"]

# mkdir -p /data/db
# mongod --dbpath /data/db --bind_ip 0.0.0.0

# redis-server
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# npm run dev -- --host