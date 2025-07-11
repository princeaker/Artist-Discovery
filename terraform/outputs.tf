output "airflow_public_ip" {
  value = aws_instance.airflow-server.public_ip
}

output "metabase_public_ip" {
  value = aws_instance.metabase-server.public_ip
}

output "private_key" {
  value     = tls_private_key.custom_key.private_key_pem
  sensitive = true
}

output "metabase_private_key" {
  value     = tls_private_key.metabase_custom_key.private_key_pem
  sensitive = true
}

output "rds_endpoint" {
  value = aws_db_instance.airflow_postgres.address
}
