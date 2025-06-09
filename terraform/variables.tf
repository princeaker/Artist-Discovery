
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "key_name" {
  description = "EC2 key name"
  type        = string
  default     = "sde-key"
}


variable "airflow_admin_password" {
  description = "EC2 airflow password"
  type        = string
}

variable "db_password" {
  description = "Database password"
  type        = string
}

## Your repository url
variable "repo_url" {
  description = "Repository url to clone into production machine"
  type        = string
  default     = "https://github.com/princeaker/Artist-Discovery"
}

variable "iss" {
  description = "Issuer for apple authentication"
  type        = string
}

variable "apple_private_key" {
  description = "Apple private key used to sign JWT tokens"
  type        = string
}

variable "kid" {
  description = "key identifer obtained from apple developer account"
  type        = string
}