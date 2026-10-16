# Internet -> ingress node on 80/443 only. Attached to the ingress node group alone:
# the application nodes stay in private subnets without public IPs.
resource "aws_security_group" "ingress_public" {
  count       = var.public_ingress_node ? 1 : 0
  name        = "${var.project}-ingress-public"
  description = "HTTP/HTTPS from the internet to the ingress-nginx edge node"
  vpc_id      = module.vpc.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "ingress_http" {
  for_each          = var.public_ingress_node ? toset(["80", "443"]) : toset([])
  security_group_id = aws_security_group.ingress_public[0].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = tonumber(each.value)
  to_port           = tonumber(each.value)
  description       = "public web traffic to ingress-nginx"
}
