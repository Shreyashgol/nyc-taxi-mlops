# S0: expose the outputs listed in contracts/runtime.yaml under terraform_outputs.
# scripts/register-runner.sh, scripts/catch-up.sh and the grader read them by those names.

output "app_public_ip" {
  value       = module.app.public_ip
  description = "Public Elastic IP of the app host"
}

output "app_instance_id" {
  value       = module.app.instance_id
  description = "EC2 instance ID of the app host"
}

output "platform_instance_id" {
  value       = module.platform.instance_id
  description = "EC2 instance ID of the platform host"
}

output "llm_instance_id" {
  value       = module.llm.instance_id
  description = "EC2 instance ID of the LLM host"
}

output "rds_endpoint" {
  value       = module.rds.endpoint
  description = "Postgres endpoint for RDS"
}

output "artifact_bucket" {
  value       = module.artifact_bucket.name
  description = "S3 bucket for MLflow artifacts and datasets"
}

output "app_private_ip" {
  value       = module.app.private_ip
  description = "Private IP of the app host"
}

output "platform_private_ip" {
  value       = module.platform.private_ip
  description = "Private IP of the platform host"
}

output "llm_private_ip" {
  value       = module.llm.private_ip
  description = "Private IP of the LLM host"
}
