FROM python:3.13
WORKDIR /usr/local/app

# Install dependencies
COPY requirements.txt ./
RUN apt-get update && apt-get install nano
RUN pip install -r requirements.txt