locals {
  name = "${var.project}-eks"
  azs  = slice(data.aws_availability_zones.available.names, 0, 2)
}

# ---------------------------------------------------------------------------
# Network: 2 AZs, each with a public subnet (load balancers, NAT) and a
# private subnet (worker nodes). One NAT gateway keeps the classroom bill low;
# production would use one per AZ.
# ---------------------------------------------------------------------------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "6.7.3"

  name = "${var.project}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  public_subnets  = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, 100 + i)] # 10.40.100.0/24, 10.40.101.0/24
  private_subnets = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, i)]       # 10.40.0.0/24,   10.40.1.0/24

  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true

  # tell Kubernetes where it may place internet-facing vs internal load balancers
  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }
}

# ---------------------------------------------------------------------------
# EKS control plane + one managed node group in the private subnets
# ---------------------------------------------------------------------------
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.29.0"

  name               = local.name
  kubernetes_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  endpoint_public_access       = true
  endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs
  endpoint_private_access      = true

  # the IAM identity running `terraform apply` becomes cluster admin (EKS access entries, no aws-auth ConfigMap)
  enable_cluster_creator_admin_permissions = true
  authentication_mode                      = "API"

  # add-ons get AWS permissions through EKS Pod Identity, so the IRSA OIDC provider is not needed
  enable_irsa = false

  # Short-lived classroom cluster: skip the KMS key (billed for 7+ days after deletion) and
  # control-plane logs (CloudWatch ingestion). Production: enable both.
  create_kms_key              = false
  encryption_config           = null
  create_cloudwatch_log_group = false
  enabled_log_types           = []

  addons = {
    vpc-cni = {
      before_compute = true # networking must exist before nodes join
    }
    kube-proxy = {}
    coredns    = {}
    eks-pod-identity-agent = {
      before_compute = true
    }
    # PersistentVolumes for PostgreSQL; IAM via EKS Pod Identity (see ebs-csi.tf)
    aws-ebs-csi-driver = {
      pod_identity_association = [{
        role_arn        = aws_iam_role.ebs_csi.arn
        service_account = "ebs-csi-controller-sa"
      }]
    }
    # resource metrics for `kubectl top` and the HorizontalPodAutoscaler
    metrics-server = {}
  }

  eks_managed_node_groups = {
    general = {
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      capacity_type  = var.node_capacity_type

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      disk_size = 20

      labels = { workload = "general" }
    }
  }

  access_entries = var.github_repository == "" ? {} : {
    github_actions = {
      principal_arn = aws_iam_role.github_deploy[0].arn
      policy_associations = {
        # cluster-wide because the chart also manages monitoring.coreos.com resources (ServiceMonitor,
        # PrometheusRule). Tighten to a namespace-scoped AmazonEKSEditPolicy if you drop those.
        admin = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }
}
