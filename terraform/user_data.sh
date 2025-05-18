#!/bin/bash
apt-get update -y
apt-get install -y python3-pip python3-venv libpq-dev curl unzip awscli


# Create a virtual environment
python3 -m venv /opt/airflow_venv
source /opt/airflow_venv/bin/activate

# Install Airflow
export AIRFLOW_HOME=/opt/airflow
pip install "apache-airflow[celery,postgres,amazon]==2.7.0" --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.7.0/constraints-3.8.txt"

# Initialize Airflow
mkdir -p $AIRFLOW_HOME
cd $AIRFLOW_HOME
airflow db init

ADMIN_PASSWORD=$(aws ssm get-parameter --name "/airflow/admin_password" --with-decryption --region us-east-2 --query "Parameter.Value" --output text)


# Create user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password "$ADMIN_PASSWORD"

# Start services (you may want to run these via systemd instead)
nohup airflow webserver --port 8080 > /opt/airflow/webserver.log 2>&1 &

# HEALTH CHECK: Wait for Airflow webserver to be healthy
AIRFLOW_URL="http://localhost:8080/health"
echo "🔍 Waiting for Airflow webserver to become healthy at $AIRFLOW_URL..."

for i in {1..30}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$AIRFLOW_URL")
  if [ "$STATUS" -eq 200 ]; then
    echo "✅ Airflow webserver is healthy!"
    break
  else
    echo "⏳ Still waiting... (Attempt $i/30)"
    sleep 5
  fi
done

nohup airflow scheduler > /opt/airflow/scheduler.log 2>&1 &