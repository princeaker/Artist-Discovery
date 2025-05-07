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

}

# resource "aws_instance" "pipeline-server" {
#   ami           = "ami-060a84cbcb5c14844"
#   instance_type = "t2.micro"

#   tags = {
#     Name = "PipelineServer"
#   }
# }

# resource "aws_vpc" "artist-discovery-vpc" {
#   cidr_block = "10.0.0.0/16"

#   tags = {
#     Name = "production"
#   }
# }

# resource "aws_subnet" "subnet-1" {
#   vpc_id     = aws_vpc.artist-discovery-vpc.id
#   cidr_block = "10.0.1.0/24"

#   tags = {
#     Name = "prod-subnet"
#   }
# }