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

# 3. IAM Role and Policy for SSM Access
resource "aws_iam_role" "ec2_ssm_role" {
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
}

resource "aws_iam_policy_attachment" "ssm_attach" {
  name       = "attach-ssm"
  roles      = [aws_iam_role.ec2_ssm_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}

resource "aws_iam_instance_profile" "ec2_instance_profile" {
  name = "ec2-airflow-profile"
  role = aws_iam_role.ec2_ssm_role.name
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

resource "aws_instance" "airflow-server" {
  ami           = "ami-060a84cbcb5c14844"
  instance_type = "t2.micro"
  key_name    = aws_key_pair.generated_key.key_name
  iam_instance_profile = aws_iam_instance_profile.ec2_instance_profile.name
  subnet_id = aws_subnet.subnet-1.id
  vpc_security_group_ids = [aws_security_group.airflow_security_group.id]


  user_data = file("user_data.sh")

  tags = {
    Name = "Airflow-Server"
  }
}

