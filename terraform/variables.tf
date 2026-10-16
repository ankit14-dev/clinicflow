variable "aws_region" {
  description = "AWS region for every resource"
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix and Project tag"
  type        = string
  default     = "clinicflow"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Owner tag, so classroom resources can be traced to a student"
  type        = string
  default     = "ankit-kumar"
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC"
  type        = string
  default     = "10.40.0.0/16"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version. Keep it in *standard* support: extended support costs 6x per cluster-hour"
  type        = string
  default     = "1.36"
}

variable "node_instance_types" {
  description = "Instance types of the managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_capacity_type" {
  description = "ON_DEMAND or SPOT (SPOT is ~60-70% cheaper but nodes can be reclaimed)"
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.node_capacity_type)
    error_message = "node_capacity_type must be ON_DEMAND or SPOT."
  }
}

variable "node_desired_size" {
  description = "Initial number of worker nodes"
  type        = number
  default     = 3
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 4
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "Who may reach the public Kubernetes API endpoint. GitHub-hosted runners need it for the deploy job"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "github_repository" {
  description = "owner/repo allowed to deploy through GitHub Actions OIDC (empty string disables the deploy role)"
  type        = string
  default     = "ankit14-dev/clinicflow"
}

variable "github_environment" {
  description = "GitHub Actions environment used by the deploy job (part of the OIDC subject claim)"
  type        = string
  default     = "production"
}
