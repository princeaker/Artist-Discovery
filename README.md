# Artist-Discovery

## Overview
As an avid music lover, I wanted to make a project that I would use for myself. I love discovering new music and finding shows that I can attend so I thought it would be a great idea to make a dashboard that shows me the latest album releases and any upcoming shows that thoses artists might have.  In this project I built a data pipeline to ingest data from Apple Music and Seatgeek APIs to serve data through a dashboard on the latest shows from artists with popular new albums. 

To run this project you'll need to meet several prerequisites:
- Have Terraform installed. The project can be started by using Terraform apply
- Create a developer account with Apple
- Create a developer account with Seatgeek
- In addition I created the S3 buckets through the UI rather than provision them through Terraform

## Data Sources
There are two main data sources. 

**Apple Music API**

The API is used to interact with the charts endpoint to obtain the most-played albums of the day.

The Apple Music API requires you to set up a developer account with a $100 fee. Once an account is created Apple requires that you use a JWT token to interact with their API. The JWT token will require the below items. These are stored in AWS SSM.
* 10-character key identifier (kid) key, obtained from your developer account
* The issuer (iss) registered claim key, which is a 10-character Team ID obtained from the developer account

**Seatgeek API**

The Seatgeek API is used to find upcoming events for artists identified from the most-played albums.

Seatgeek requires a developer account to interact with their API. Once I registered on the site I needed to email their team to approve my account.

## Architecture
My goal with this project was to build the data pipeline and dashboard in a low-cost, scalable, and as close to production-grade as possible.

## Infrastructure Layer
### Terraform
Used to provision all resources in the architecture:

EC2 instances for Airflow and Metabase

SSM key value pairs to store passwords and other secrets

IAM roles and permissions

Glue catalog, crawlers

Security groups

## Data Pipeline Orchestration
### Apache Airflow (on EC2)
Runs a DAG with 4 sequential tasks:

🔹 Task 1: Ingest data from Apple Music API
Pulls raw data

Applies light transformation

Uploads it to S3 in a structured path

🔹 Task 2: Call SeatGeek API
Uses the Apple Music data as input

Gets related event data

Creates 2 transformed datasets

Saves both to S3

🔹 Task 3: Combine datasets
Joins Apple + SeatGeek data

Writes partitioned Parquet files to S3

Enables efficient Athena queries

🔹 Task 4: Update Glue Catalog
Triggers a Glue Crawler to crawl new data

Updates table metadata in the AWS Glue Data Catalog

## Query & Visualization Layer
### Amazon Athena
Reads the partitioned data from S3

Exposes it as SQL tables

### Metabase (on EC2)
Connects to Athena

Powers dashboards and data exploration

