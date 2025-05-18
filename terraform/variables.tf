
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

## Your repository url
variable "repo_url" {
  description = "Repository url to clone into production machine"
  type        = string
  default     = "https://github.com/princeaker/Artist-Discovery"
}