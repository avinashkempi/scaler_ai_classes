# ClaimSense | Author: Shivank Agrawal
variable "aws_region" {
  description = "AWS region to deploy into (ap-south-1 = Mumbai)"
  type        = string
  default     = "ap-south-1"
}

variable "app_name" {
  description = "Prefix for every resource name"
  type        = string
  default     = "claimsense"
}

variable "image_tag" {
  description = "Docker image tag pushed to ECR by deploy.sh"
  type        = string
  default     = "latest"
}

variable "allowed_cidr" {
  description = "Who can open the portal/API. Use your own IP like 49.36.10.20/32 for anything beyond a demo"
  type        = string
  default     = "0.0.0.0/0"
}

variable "openai_param_name" {
  description = "SSM Parameter Store name that holds the OpenAI key (created by deploy.sh, not by Terraform)"
  type        = string
  default     = "/claimsense/openai_api_key"
}
