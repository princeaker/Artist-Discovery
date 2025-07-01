# Artist-Discovery

## Project Overview
For my first data engineering project and as an avid music fan, I wanted to build something I'd use myself. I love discovering new music and finding shows that I can attend so I decided to create a tool that would do both. This project combines data from Apple Music and SeatGeek to surface the most popular new albums and upcoming concerts by those artists, surfaced through a dashboard.

In this project, I've used a data engineering stack built with Terraform, Airflow, and AWS services to create a low-cost, scalable, and reproducible data pipeline that ends with a functional dashboard powered by Metabase

## Tech Stack

- **Infrastructure:** AWS (EC2, S3, Glue, Athena, SSM)
- **Orchestration:** Apache Airflow (EC2)
- **Provisioning:** Terraform
- **Data Sources:** Apple Music API, SeatGeek API
- **Dashboard:** Metabase (EC2)

## Data Sources
There are two main data sources. 

### Apple Music API

The API is used to interact with the charts endpoint to obtain the most-played albums of the day.

The Apple Music API requires you to set up a developer account with a $100 fee. Once an account is created Apple requires that you use a JWT token to interact with their API. The JWT token will require the below items. These are stored in AWS SSM.
* 10-character key identifier (kid) key, obtained from your developer account
* The issuer (iss) registered claim key, which is a 10-character Team ID obtained from the developer account

### Seatgeek API

The Seatgeek API is used to find upcoming events for artists identified from the most-played albums.

Seatgeek requires a developer account to interact with their API. Once I registered my account I needed to email their team to approve my account.

## Architecture
Below is the breakdown of the infrastructure and pipeline.


### Infrastructure Layer (Terraform)
- Used to provision all resources in the architecture (except for S3 bucket):
- EC2 instances for Airflow and Metabase
- SSM key value pairs to store passwords and other secrets
- IAM roles and policies
- Glue catalog, crawlers
- Security groups

## Data Pipeline Orchestration
### Apache Airflow (on EC2)
Runs a DAG with 4 sequential tasks:

1. Ingest data from Apple Music API
- Pulls raw data
- Applies light transformation on JSON
- Uploads to S3 as a parquet file

2. Ingest SeatGeek Events
- Uses the Apple Music data as input
- Gets related event data
- Creates 2 transformed datasets
- Saves both to S3

3. Combine datasets
- Joins Apple + SeatGeek data
- Writes partitioned Parquet files to S3
- Enables efficient Athena queries

4. Update Glue Catalog
- Triggers a Glue Crawler to crawl new data
- Updates table metadata for Athena

### Query & Visualization Layer
- **Amazon Athena**: Queries partitioned data in S3
- **Metabase**: Powers user-friendly dashboard

## Setup Instructions

To run this project you'll need to meet several prerequisites:
- Have Terraform installed. The project can be started by using Terraform apply
- AWS account with permissions to provision EC2, SSM, IAM, Glue, etc.
- Create a developer account with Apple
- Create a developer account with Seatgeek
- In addition I created the S3 buckets through the UI rather than provision them through Terraform

## Future Improvements
- Provision S3 buckets with Terraform
- Modularize Terraform code
- Place Airflow within a container
- Setup CI/CD for DAG deployment
- unit test for API extractors with Great Expectations
