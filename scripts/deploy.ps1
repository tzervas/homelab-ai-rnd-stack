# Deploy Homelab AI R&D Stack
param(
    [string]$Host = "localhost",
    [string]$Domain = "homelab.lan",
    [string]$MetalLBRange = "192.168.1.200-192.168.1.210",
    [string]$StoragePath = "/mnt/k8s-data",
    [string]$K3sVersion = "v1.28.5+k3s1",
    [switch]$Initialize
)

# Check requirements
$requiredCommands = @("ansible", "git", "helm")
foreach ($cmd in $requiredCommands) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "Required command '$cmd' not found. Please install it first."
        exit 1
    }
}

# Create directories if initializing
if ($Initialize) {
    $directories = @(
        "charts",
        "deployments/core",
        "deployments/dev",
        "deployments/gitlab",
        "deployments/monitoring",
        "templates",
        "overrides/global",
        "overrides/components"
    )

    foreach ($dir in $directories) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    }
}

# Create inventory file for Ansible
$inventoryContent = @"
[k3s_nodes]
$Host ansible_connection=local
"@
Set-Content -Path "scripts/ansible/inventory" -Value $inventoryContent

# Set environment variables
$env:K3S_VERSION = $K3sVersion
$env:METALLB_IP_RANGE = $MetalLBRange
$env:STORAGE_PATH = $StoragePath
$env:DOMAIN = $Domain

# Run Ansible playbook
Write-Host "Installing K3s and bootstrapping cluster..."
ansible-playbook -i scripts/ansible/inventory scripts/ansible/k3s-install.yml

# Verify cluster access
kubectl get nodes
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to access Kubernetes cluster"
    exit 1
}

# Deploy core components via ArgoCD
Write-Host "Deploying core components..."

# Create namespaces
$namespaces = @(
    "metallb-system",
    "ingress-nginx",
    "cert-manager",
    "monitoring",
    "gitlab",
    "jupyter",
    "ollama"
)

foreach ($ns in $namespaces) {
    kubectl create namespace $ns --dry-run=client -o yaml | kubectl apply -f -
}

# Add Helm repositories
$helmRepos = @{
    "ingress-nginx" = "https://kubernetes.github.io/ingress-nginx"
    "jetstack" = "https://charts.jetstack.io"
    "metallb" = "https://metallb.github.io/metallb"
    "gitlab" = "https://charts.gitlab.io"
    "jupyter" = "https://jupyter.github.io/helm-chart"
    "prometheus-community" = "https://prometheus-community.github.io/helm-charts"
}

foreach ($repo in $helmRepos.GetEnumerator()) {
    helm repo add $repo.Key $repo.Value
}
helm repo update

# Initialize ArgoCD with our configuration
Write-Host "Configuring ArgoCD..."
kubectl apply -f deployments/core/argocd/values.yaml -n argocd

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# Get ArgoCD admin password
$argoCDPassword = kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }

# Save access information
$accessInfo = @"
Homelab AI R&D Stack Access Information
=====================================

ArgoCD:
  URL: https://argocd.$Domain
  Username: admin
  Password: $argoCDPassword

Ingress IP Ranges:
  MetalLB: $MetalLBRange

Access URLs:
  GitLab:     https://gitlab.$Domain
  JupyterLab: https://jupyter.$Domain
  Ollama:     https://ollama.$Domain
  Grafana:    https://grafana.$Domain

Default Credentials:
  GitLab: root / <check initial root password>
  Grafana: admin / admin (change on first login)
  JupyterLab: <token shown in pod logs>
"@

Set-Content -Path "access-info.txt" -Value $accessInfo

Write-Host "Deployment completed!"
Write-Host "Access information saved to access-info.txt"
Write-Host @"

Next Steps:
1. Configure DNS entries for:
   - argocd.$Domain
   - gitlab.$Domain
   - jupyter.$Domain
   - ollama.$Domain
   - grafana.$Domain

2. Access ArgoCD at https://argocd.$Domain
   Username: admin
   Password: $argoCDPassword

3. Monitor deployment progress in ArgoCD UI

4. See access-info.txt for all credentials
"@
