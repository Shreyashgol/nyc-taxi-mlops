# S0: security groups and rules.
#
# Decision point: who may reach the app (ingress scope)? Record it in decisions/.
# Traffic between hosts (ports in contracts/runtime.yaml):
#   app -> platform  MLflow (5000)
#   app, platform -> llm  chat (8080) and embeddings (8081)
#   app, platform -> rds  Postgres (5432)
# There is no SSH in this lab: use SSM Session Manager for a shell and port forwarding for UIs.

# App host: Traefik on port 80
resource "aws_security_group" "app" {
  name        = "lab-app"
  description = "Security group for app host"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP traffic to Traefik"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.ingress_cidrs
  }

  egress {
    description = "Outbound to all (SSM, GHCR, internet)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lab-app"
  }
}

# Platform host: MLflow (port 5000), Dagster (port 3000 forwarded via SSM)
resource "aws_security_group" "platform" {
  name        = "lab-platform"
  description = "Security group for platform host"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "MLflow from app host"
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    description = "Outbound to all"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lab-platform"
  }
}

# LLM host: chat (8080) and embeddings (8081)
resource "aws_security_group" "llm" {
  name        = "lab-llm"
  description = "Security group for LLM host"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "LLM chat and embed from app and platform"
    from_port       = 8080
    to_port         = 8081
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id, aws_security_group.platform.id]
  }

  egress {
    description = "Outbound to all"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lab-llm"
  }
}

# RDS Postgres: port 5432
resource "aws_security_group" "rds" {
  name        = "lab-rds"
  description = "Security group for RDS Postgres"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Postgres from app and platform"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id, aws_security_group.platform.id]
  }

  egress {
    description = "Outbound to all"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lab-rds"
  }
}
