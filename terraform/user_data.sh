#!/bin/bash
set -e

# Update system and install dependencies for Amazon Linux
yum update -y
yum install -y python3 python3-pip python3-virtualenv postgresql-devel gcc gcc-c++ unzip jq libxml2-devel xmlsec1-devel xmlsec1-openssl-devel libtool-ltdl-devel

DB_HOST="${db_host}"
DB_NAME="${db_name}"
DB_USER="${db_user}"

# Create a virtual environment
python3 -m venv /opt/airflow_venv
source /opt/airflow_venv/bin/activate

# Install Airflow with Postgres driver
AIRFLOW_VERSION=2.10.5
PYTHON_VERSION=$(python --version | awk '{print $2}' | cut -d. -f1,2)
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-$${AIRFLOW_VERSION}/constraints-$${PYTHON_VERSION}.txt"

DB_PASSWORD=$(aws ssm get-parameter --name "/airflow/db_password" --with-decryption --region us-east-2 --query "Parameter.Value" --output text)

pip install "apache-airflow==$${AIRFLOW_VERSION}" --constraint "$${CONSTRAINT_URL}"
pip install psycopg2-binary
pip install "apache-airflow==$${AIRFLOW_VERSION}" "apache-airflow-providers-amazon"
pip install pyjwt[crypto]
pip install pandas==2.2.3
pip install pyarrow==19.0.1


export AIRFLOW_HOME=/opt/airflow
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__LOGGING__BASE_LOG_FOLDER=/opt/airflow/logs
export AIRFLOW__CORE__SQL_ALCHEMY_CONN="postgresql+psycopg2://$${DB_USER}:$${DB_PASSWORD}@$${DB_HOST}:5432/$${DB_NAME}"
export AIRFLOW__WEBSERVER__SECRET_KEY=$(openssl rand -hex 16)

mkdir -p $${AIRFLOW_HOME}
cd $${AIRFLOW_HOME}
airflow db init

ADMIN_PASSWORD=$(aws ssm get-parameter --name "/airflow/admin_password" --with-decryption --region us-east-2 --query "Parameter.Value" --output text)

airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password "$${ADMIN_PASSWORD}"

aws s3 sync s3://project-dags/dags/ /opt/airflow/dags/ --region us-east-2


# Start Airflow
nohup airflow webserver --port 8080 > /opt/airflow/webserver.log 2>&1 &
nohup airflow scheduler > /opt/airflow/scheduler.log 2>&1 &

