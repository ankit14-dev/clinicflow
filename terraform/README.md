# Terraform: AWS VPC + EKS for ClinicFlow

Creates, in `ap-south-1` (Mumbai):

```text
VPC 10.40.0.0/16
├── public subnets   10.40.100.0/24, 10.40.101.0/24   (2 AZs) ── Internet Gateway, NAT Gateway, the NLB from ingress-nginx
├── private subnets  10.40.0.0/24,   10.40.1.0/24     (2 AZs) ── worker nodes (no public IPs), egress via NAT
└── EKS cluster clinicflow-eks (Kubernetes 1.36, API access entries)
      ├── managed node group "general": 3 x t3.medium (min 2 / max 4), Amazon Linux 2023
      └── add-ons: vpc-cni, kube-proxy, coredns, eks-pod-identity-agent, aws-ebs-csi-driver, metrics-server
IAM
├── clinicflow-ebs-csi        EBS CSI driver role via EKS Pod Identity
└── clinicflow-github-deploy  assumed by GitHub Actions through OIDC (no AWS keys stored in GitHub)
```

## Prerequisites

* AWS CLI configured (`aws sts get-caller-identity` works). The IAM user needs EC2, IAM and **EKS** permissions;
  the extra EKS policy is in [`../docs/aws-iam-eks-policy.json`](../docs/aws-iam-eks-policy.json).
* Terraform >= 1.10, kubectl, Helm 4.

## Run

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # optional, defaults already work
terraform init
terraform fmt -check && terraform validate
terraform plan -out clinicflow.tfplan           # 59 resources to add
terraform apply clinicflow.tfplan               # ~15 minutes
cd .. && ./scripts/eks-up.sh                    # kubeconfig + monitoring + ingress controller
```

## Destroy (do this the same day)

```bash
./scripts/eks-down.sh     # removes the NLB and EBS volumes Kubernetes created, then `terraform destroy`
```

`terraform destroy` alone is not enough: the load balancer and the PostgreSQL volume are created by Kubernetes,
not by Terraform. If they still exist, destroy hangs on the VPC and the volumes keep costing money.

## Cost (ap-south-1, on-demand, approximate)

| Resource | $/hour |
|---|---|
| EKS control plane (standard support) | 0.10 |
| 3 × t3.medium nodes | ~0.13 |
| NAT Gateway (+ data) | ~0.06 |
| Network Load Balancer | ~0.02 |
| EBS (nodes 3×20 GB + PVCs) | ~0.01 |
| **Total** | **≈ $0.32/hour** — a 3-hour demo ≈ $1 |

Keep `kubernetes_version` in standard support: in extended support the control plane costs $0.60/hour.
`node_capacity_type = "SPOT"` cuts the node cost by roughly two thirds.

## Design decisions

* **Nodes in private subnets** — workers are not reachable from the internet; only the NLB is public.
* **Single NAT gateway** — saves ~$0.06/hour per extra AZ; production would use one per AZ.
* **No KMS key / control-plane logs** — a KMS key is billed for 7+ days after deletion and logs cost CloudWatch
  ingestion; both should be enabled for a long-lived cluster.
* **State is local** (`terraform.tfstate`, git-ignored). For a team, use an S3 backend with `use_lockfile = true`.
* **Least privilege for CI** — the GitHub role can only `eks:DescribeCluster` in AWS, and the trust policy only
  accepts tokens from `repo:ankit14-dev/clinicflow:environment:production`.
