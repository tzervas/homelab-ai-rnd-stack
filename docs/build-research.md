# Build Research & Technical Decisions

## Component Versions & Selection Rationale

### Core Infrastructure

#### Kubernetes Platform
- **K3s v1.28.5**
  - Lightweight distribution ideal for homelab
  - Built-in containerd
  - Single binary installation
  - Low resource overhead
  - Embedded etcd (no external DB needed)

#### Load Balancer & Ingress
- **MetalLB v0.13.12**
  - L2 configuration for homelab environment
  - Simple IP pool management
  - ARP/NDP support for Layer 2 mode
  - Compatible with K3s

- **NGINX Ingress Controller v1.9.5**
  - Stable and well-tested
  - Low resource footprint
  - Good documentation
  - SSL termination support
  - Custom header support

#### Certificate Management
- **cert-manager v1.13.3**
  - Automated TLS management
  - Let's Encrypt integration
  - Self-signed capability
  - Internal CA support

### Development Environment

#### JupyterLab
- **JupyterLab v4.1.2**
  - Full-featured IDE
  - Notebook support
  - Extension ecosystem
  - Git integration
  - Terminal access

#### AI Infrastructure
- **Ollama v0.1.27**
  - Local LLM hosting
  - Model management
  - API support
  - GPU acceleration

- **Ollama Web UI v0.1.27**
  - Clean interface
  - Chat functionality
  - Model switching
  - System prompt management

### CI/CD & Version Control

#### GitLab
- **GitLab CE v16.6.0**
  - Integrated CI/CD
  - Container registry
  - Issue tracking
  - Wiki support
  - Built-in monitoring

#### GitLab Runner
- **GitLab Runner v16.6.0**
  - Docker executor
  - Kubernetes executor support
  - Resource constraints
  - Cache management

### Monitoring & Observability

#### Metrics
- **Prometheus v2.45.3**
  - Time-series database
  - Pull-based architecture
  - Alert management
  - Service discovery

- **Grafana v10.2.3**
  - Dashboard creation
  - Alert integration
  - Variable support
  - Plugin ecosystem

## Technical Decisions

### 1. Networking Architecture

#### Pod Network
```yaml
network_config:
  pod_network_cidr: "10.0.0.0/16"
  service_cidr: "10.1.0.0/16"
  dns_service_ip: "10.1.0.10"
```

**Rationale:**
- Large pod CIDR for growth
- Separate service network
- Standard DNS IP location
- No overlap with typical LAN ranges

#### MetalLB Configuration
```yaml
metalLB:
  ipAddressPool:
    name: "default"
    addresses:
      - "192.168.1.200-192.168.1.210"
  mode: "layer2"
```

**Rationale:**
- Reserved IP range for services
- Layer 2 mode for simplicity
- Multiple IPs for service separation
- Easy DNS configuration

### 2. Storage Architecture

#### Local Path Provisioner
```yaml
local_path:
  path: "/mnt/k8s-data"
  node_paths:
    - "/mnt/k8s-data-1"
    - "/mnt/k8s-data-2"
```

**Rationale:**
- Simple local storage
- Multiple paths for flexibility
- Direct path access
- No external dependencies

#### Storage Classes
```yaml
storage_classes:
  default:
    name: "local-path"
    provisioner: "rancher.io/local-path"
  fast:
    name: "local-nvme"
    provisioner: "rancher.io/local-path"
    parameters:
      path: "/mnt/nvme-data"
```

**Rationale:**
- Multiple storage options
- Performance tiering
- Simple management
- Local access speed

### 3. Security Decisions

#### Network Policies
```yaml
default_network_policies:
  deny_all:
    enabled: true
  allow_dns:
    enabled: true
  allow_metrics:
    enabled: true
```

**Rationale:**
- Zero-trust networking
- Explicit allow rules
- Basic service access
- Monitoring support

#### RBAC Configuration
```yaml
rbac_config:
  default_user_role: "view"
  admin_role: "cluster-admin"
  service_accounts:
    prometheus:
      role: "monitoring"
    gitlab_runner:
      role: "runner"
```

**Rationale:**
- Minimal privileges
- Service isolation
- Clear role definitions
- Easy management

### 4. Monitoring Architecture

#### Prometheus Configuration
```yaml
prometheus:
  retention:
    time: 15d
    size: 10GB
  scrape_interval: 30s
  evaluation_interval: 30s
```

**Rationale:**
- Balanced retention
- Regular updates
- Resource consideration
- Alert responsiveness

#### Grafana Setup
```yaml
grafana:
  persistence:
    enabled: true
    size: 5Gi
  plugins:
    - grafana-piechart-panel
    - grafana-clock-panel
```

**Rationale:**
- Persistent dashboards
- Essential plugins
- Moderate storage
- User customization

## Integration Points

### 1. External DNS Integration
- Route53 automation tool integration points
- Automated DNS record management
- Domain verification
- Split DNS support

### 2. Authentication Flow
- Local accounts for initial setup
- Future SSO integration points
- Service account management
- Token-based auth

### 3. Backup Integration
- Volume snapshot locations
- GitLab backup strategy
- Configuration backups
- Disaster recovery

### 4. Monitoring Integration
- Service discovery
- Custom metrics
- Alert routing
- Dashboard templates

## Resource Requirements

### Minimum Specifications
- **CPU**: 4 cores
- **RAM**: 16GB
- **Storage**: 100GB
- **Network**: 1Gbps

### Recommended Specifications
- **CPU**: 8 cores
- **RAM**: 32GB
- **Storage**: 500GB SSD
- **Network**: 1Gbps+

### Component Requirements

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|------------|-----------|----------------|--------------|
| GitLab CE | 2 cores | 4 cores | 8GB | 12GB |
| JupyterLab | 1 core | 2 cores | 2GB | 4GB |
| Ollama | 2 cores | 4 cores | 4GB | 8GB |
| Prometheus | 0.5 cores | 1 core | 2GB | 4GB |
| Grafana | 0.2 cores | 0.5 cores | 256MB | 512MB |
| NGINX | 0.2 cores | 0.5 cores | 256MB | 512MB |

## Environment Variables

### Core Settings
```bash
# Cluster Configuration
KUBERNETES_VERSION="v1.28.5+k3s1"
POD_NETWORK_CIDR="10.0.0.0/16"
SERVICE_CIDR="10.1.0.0/16"

# MetalLB Configuration
METALLB_IP_RANGE="192.168.1.200-192.168.1.210"
METALLB_VERSION="v0.13.12"

# Storage Configuration
LOCAL_PATH="/mnt/k8s-data"
STORAGE_CLASS="local-path"

# GitLab Configuration
GITLAB_VERSION="16.6.0-ce.0"
GITLAB_DOMAIN="gitlab.lan"
GITLAB_RUNNERS=2
```

### Security Settings
```bash
# TLS Configuration
CERT_MANAGER_VERSION="v1.13.3"
LETS_ENCRYPT_EMAIL="admin@homelab.lan"
USE_PRODUCTION_LETSENCRYPT=false

# Monitoring
PROMETHEUS_RETENTION="15d"
GRAFANA_ADMIN_PASSWORD="${SECURE_PASSWORD}"
```

## Configuration Files

### 1. Global Values
```yaml
# global-values.yaml
global:
  environment: "homelab"
  domain: "homelab.lan"
  storageClass: "local-path"
  monitoring:
    enabled: true
    retention: "15d"
  security:
    networkPolicies: true
    tlsEnabled: true
```

### 2. Component Values
```yaml
# gitlab-values.yaml
gitlab:
  edition: ce
  version: "16.6.0-ce.0"
  runners:
    replicas: 2
    executor: docker
  persistence:
    enabled: true
    size: 50Gi
```

## Initial Setup Commands

### 1. K3s Installation
```bash
curl -sfL https://get.k3s.io | sh -s - \
  --write-kubeconfig-mode 644 \
  --disable traefik \
  --disable servicelb \
  --disable metrics-server \
  --flannel-backend=host-gw \
  --cluster-cidr="10.0.0.0/16" \
  --service-cidr="10.1.0.0/16"
```

### 2. MetalLB Setup
```bash
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.12/config/manifests/metallb-native.yaml
```

### 3. NGINX Ingress
```bash
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --values nginx-values.yaml
```

These technical decisions and configurations form the foundation of our minimal but robust homelab AI cluster. They prioritize simplicity, security, and maintainability while providing all necessary functionality for AI development and GitLab CI/CD capabilities.
