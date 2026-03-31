# 1. Define the Subnet Group (Required since you're creating a new one)
resource "aws_db_subnet_group" "sra_subnet_group" {
  name       = "sra-demo-db-subnet-group"
  # Replace these with the actual subnet IDs from your VPC: vpc-032ceb81
  subnet_ids = ["subnet-xxxxxxxx", "subnet-yyyyyyyy"] 

  tags = {
    Name = "SRA Demo DB Subnet Group"
  }
}

# 2. Define the RDS Instance
resource "aws_db_instance" "sra_demo_db" {
  identifier           = "sra-demo-db"
  engine               = "mysql"
  engine_version       = "8.4" # Matches your parameter group request
  instance_class       = "db.m7g.large" # Graviton3 Standard Class
  
  # Credentials
  username             = "admin"
  password             = "YourSecurePassword123!" # Recommend using Secrets Manager in production
  db_name              = "sra_demo_db"
  port                 = 3306

  # Storage Configuration
  storage_type         = "io2"
  allocated_storage    = 400
  iops                = 3000

  # Network & Security
  db_subnet_group_name   = aws_db_subnet_group.sra_subnet_group.name
  vpc_security_group_ids = ["sg-xxxxxxxx"] # Replace with your 'default' SG ID
  publicly_accessible    = false
  multi_az               = false
  ca_cert_identifier     = "rds-ca-rsa2048-g1"

  # DB Parameters & Options
  parameter_group_name = "default.mysql8.4"
  option_group_name    = "default:mysql-8-4"

  # Backup & Maintenance
  backup_retention_period = 7
  backup_window           = "03:00-04:00" # 'No preference' usually defaults to a system window
  copy_tags_to_snapshot   = true
  skip_final_snapshot     = false

  # Encryption
  storage_encrypted    = true
  kms_key_id           = "alias/aws/rds" # Default AWS KMS key

  # Deletion Protection
  deletion_protection  = true

  tags = {
    Environment = "Sandbox"
    Project     = "SRA-Demo"
  }
}