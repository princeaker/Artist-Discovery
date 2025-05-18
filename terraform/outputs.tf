output "airflow_public_ip" {
  value = aws_instance.airflow-server.public_ip
}

output "private_key" {
  value     = tls_private_key.custom_key.private_key_pem
  sensitive = true
}