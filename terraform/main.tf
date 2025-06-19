terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = "us-east-2"

}

resource "aws_vpc" "artist-discovery-vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "production"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.artist-discovery-vpc.id
}


resource "aws_subnet" "subnet-1" {
  vpc_id     = aws_vpc.artist-discovery-vpc.id
  cidr_block = "10.0.1.0/24"
  map_public_ip_on_launch = true

  tags = {
    Name = "prod-subnet"
  }
}

resource "aws_subnet" "private_subnet_1" {
  vpc_id                  = aws_vpc.artist-discovery-vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-2a"
  map_public_ip_on_launch = false
}

resource "aws_subnet" "private_subnet_2" {
  vpc_id                  = aws_vpc.artist-discovery-vpc.id
  cidr_block              = "10.0.3.0/24"
  availability_zone       = "us-east-2b"
  map_public_ip_on_launch = false
}

resource "aws_db_subnet_group" "airflow_db_subnet_group" {
  name       = "airflow-db-subnet-group"
  subnet_ids = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]

  tags = {
    Name = "Airflow DB Subnet Group"
  }
}

resource "aws_db_instance" "airflow_postgres" {
  identifier              = "airflow-postgres"
  engine                  = "postgres"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  db_name                 = "airflowdb"
  username                = "airflowuser"
  password                = var.db_password
  port                    = 5432
  db_subnet_group_name    = aws_db_subnet_group.airflow_db_subnet_group.name
  vpc_security_group_ids  = [aws_security_group.postgres_sg.id]
  publicly_accessible     = false
  skip_final_snapshot     = true
}

resource "aws_security_group" "postgres_sg" {
  name        = "postgres-sg"
  description = "Allow DB traffic from EC2"
  vpc_id      = aws_vpc.artist-discovery-vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.airflow_security_group.id]  # Airflow EC2 SG
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}


resource "aws_route_table" "public" {
  vpc_id = aws_vpc.artist-discovery-vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "basic route"
  }
}
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.subnet-1.id
  route_table_id = aws_route_table.public.id
}
# Create security group for access to EC2 from airflow
resource "aws_security_group" "airflow_security_group" {
  name        = "sde_security_group"
  description = "Security group to allow inbound SCP & outbound 8080 (Airflow) connections"
  vpc_id = aws_vpc.artist-discovery-vpc.id

  tags = {
    Name = "sde_security_group"
  }
}

resource "aws_vpc_security_group_ingress_rule" "allow_scp" {
  security_group_id = aws_security_group.airflow_security_group.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 22
  ip_protocol       = "tcp"
  to_port           = 22
}

resource "aws_vpc_security_group_egress_rule" "allow_all_ports" {
  security_group_id = aws_security_group.airflow_security_group.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" # semantically equivalent to all ports
}

resource "aws_vpc_security_group_ingress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.airflow_security_group.id
  from_port = 8080
  to_port   = 8080
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp" # semantically equivalent to all ports
}

resource "tls_private_key" "custom_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated_key" {
  key_name_prefix = var.key_name
  public_key      = tls_private_key.custom_key.public_key_openssh
}

# 3. IAM Role and Policy for AWS Resource Access
resource "aws_iam_role" "ec2_pipeline_role" {
  name = "ec2-airflow-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "ec2.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })

  max_session_duration = 7200 # 2 hours
}

resource "aws_iam_policy_attachment" "ec2_ssm_attach" {
  name       = "ec2_attach-ssm"
  roles      = [aws_iam_role.ec2_pipeline_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}

resource "aws_iam_policy_attachment" "ec2_s3_attach" {
  name       = "ec2_attach-s3"
  roles      = [aws_iam_role.ec2_pipeline_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_policy_attachment" "attach_glue" {
  name       = "ec2_attach-glue"
  roles      = [aws_iam_role.ec2_pipeline_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_instance_profile" "ec2_instance_profile" {
  name = "ec2-airflow-profile"
  role = aws_iam_role.ec2_pipeline_role.name
}

data "aws_iam_policy_document" "policy" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["*"]
  }
}

resource "aws_iam_role" "glue_role" {
  name = "glue-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "glue.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })

  max_session_duration = 7200 # 2 hours
}

resource "aws_iam_policy_attachment" "glue_policy" {
  name       = "glue_attach-policy"
  roles      = [aws_iam_role.glue_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_policy_attachment" "ssm_policy" {
  name       = "glue_attach-ssm"
  roles      = [aws_iam_role.glue_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}
resource "aws_iam_policy" "s3_policy" {
  name        = "glue-s3-policy"
  description = "Policy to allow Glue to access S3 buckets"
  policy      = data.aws_iam_policy_document.policy.json
}
resource "aws_iam_policy_attachment" "s3_policy" {
  name       = "glue_attach-s3"
  roles      = [aws_iam_role.glue_role.name]
  policy_arn = aws_iam_policy.s3_policy.arn
}


# 4. SSM Parameter
resource "aws_ssm_parameter" "airflow_admin_password" {
  name        = "/airflow/admin_password"
  type        = "SecureString"
  value       = var.airflow_admin_password # Replace or use var
  description = "Airflow admin password"

  lifecycle {
    ignore_changes = [
      value,
    ]
  }
}

resource "aws_ssm_parameter" "postgres_db_password" {
  name        = "/airflow/db_password"
  type        = "SecureString"
  value       = var.db_password
  description = "PostgreSQL db password"

  lifecycle {
    ignore_changes = [
      value,
    ]
  }
}

resource "aws_ssm_parameter" "iss" {
  name        = "/apple/iss"
  type        = "SecureString"
  value       = var.iss
  description = "Issuer for apple authentication"

  lifecycle {
    ignore_changes = [
      value,
    ]
  }
}

resource "aws_ssm_parameter" "apple_private_key" {
  name        = "/apple/private_key"
  type        = "SecureString"
  value       = var.apple_private_key
  description = "apple private key used to sign JWT tokens"

  lifecycle {
    ignore_changes = [
      value,
    ]
  }
}

resource "aws_ssm_parameter" "kid" {
  name        = "/apple/kid"
  type        = "String"
  value       = var.kid
  description = "apple private key identifer obtained from apple developer account"

  lifecycle {
    ignore_changes = [
      value,
    ]
  }
}

resource "aws_ssm_parameter" "seatgeek_client_id" {
  name        = "/seatgeek/client_key"
  type        = "String"
  value       = var.seatgeek_client_id
  description = "This is the client identifier for the SeatGeek API"

}

resource "aws_ssm_parameter" "seatgeek_client_secret" {
  name        = "/seatgeek/client_secret"
  type        = "String"
  value       = var.seatgeek_client_secret
  description = "This is the client secret for the SeatGeek API"

}

# glue job to process music albums data
# resource "aws_glue_job" "artist_discovery" {
#   name     = "artist_albums_job"
#   description = "Glue job to process music albums data"
#   role_arn = aws_iam_role.glue_role.arn

#   command {
#     name            = "pythonshell"
#     script_location = "s3://artist-discovery-scripts/get_music_albums.py"
#     python_version  = "3.9"
#   }

# # created a zip file with pyarrow and pyjwt[crypto] and uploaded to S3
# # This is used to run the Glue job with the necessary dependencies
#   default_arguments = {
#     "--extra-py-files" = "s3://artist-discovery-scripts/glue_deps.zip"
#   }

#   max_capacity = 0.0625
#   max_retries       = 0
# }


resource "aws_instance" "airflow-server" {
  ami           = "ami-06c8f2ec674c67112"
  instance_type = "t2.small"
  key_name    = aws_key_pair.generated_key.key_name
  iam_instance_profile = aws_iam_instance_profile.ec2_instance_profile.name
  subnet_id = aws_subnet.subnet-1.id
  vpc_security_group_ids = [aws_security_group.airflow_security_group.id]


  user_data = templatefile("${path.module}/user_data.sh", {
    db_host     = aws_db_instance.airflow_postgres.address,
    db_name     = "airflowdb",
    db_user     = "airflowuser"
  })

  tags = {
    Name = "Airflow-Server"
  }
}

