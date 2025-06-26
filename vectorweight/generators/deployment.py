#!/usr/bin/env python3
"""
VectorWeight Deployment Generator - PoC Version
Creates basic Kubernetes manifests and deployment structure
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from jinja2 import Template

from ..config.schema import VectorWeightConfiguration, ClusterConfiguration


class DeploymentGenerator:
    """Generate VectorWeight homelab deployment artifacts"""
    
    def __init__(self, config: VectorWeightConfiguration):
        self.config = config
        self.output_path: Path = Path("./vectorweight-deployment")
    
    def generate_complete_deployment(self) -> None:
        """Generate complete deployment structure"""
        print(f"🚀 Generating VectorWeight deployment for {self.config.project_name}")
        
        # Create output directory
        self.output_path.mkdir(exist_ok=True)
        
        # Generate for each cluster
        for cluster in self.config.clusters:
            self._generate_cluster_deployment(cluster)
        
        # Generate global resources
        self._generate_deployment_script()
        self._generate_readme()
        
        print(f"✅ Deployment generated successfully at {self.output_path}")
    
    def _generate_cluster_deployment(self, cluster: ClusterConfiguration) -> None:
        """Generate deployment artifacts for a single cluster"""
        cluster_dir = self.output_path / cluster.name
        cluster_dir.mkdir(exist_ok=True)
        
        # Create cluster structure
        (cluster_dir / "infrastructure").mkdir(exist_ok=True)
        (cluster_dir / "apps").mkdir(exist_ok=True)
        
        # Generate ArgoCD application
        self._generate_argocd_application(cluster, cluster_dir)
        
        # Generate basic infrastructure
        self._generate_basic_infrastructure(cluster, cluster_dir)
        
        print(f"  📦 Generated cluster: {cluster.name}")
    
    def _generate_argocd_application(self, cluster: ClusterConfiguration, cluster_dir: Path) -> None:
        """Generate ArgoCD application manifest"""
        app_manifest = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "name": f"{cluster.name}-infrastructure",
                "namespace": "argocd",
                "labels": {
                    "cluster": cluster.name,
                    "managed-by": "vectorweight"
                }
            },
            "spec": {
                "project": "default",
                "source": {
                    "repoURL": f"https://github.com/vectorweight/{self.config.project_name}",
                    "targetRevision": "HEAD",
                    "path": f"{cluster.name}/infrastructure"
                },
                "destination": {
                    "server": "https://kubernetes.default.svc",
                    "namespace": "default"
                },
                "syncPolicy": {
                    "automated": {
                        "prune": True,
                        "selfHeal": True
                    }
                }
            }
        }
        
        with open(cluster_dir / "application.yaml", 'w') as f:
            yaml.dump(app_manifest, f, default_flow_style=False)
    
    def _generate_basic_infrastructure(self, cluster: ClusterConfiguration, cluster_dir: Path) -> None:
        """Generate basic infrastructure manifests"""
        infra_dir = cluster_dir / "infrastructure"
        
        # Generate namespace
        namespace_manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": f"{cluster.name}-system",
                "labels": {
                    "cluster": cluster.name,
                    "managed-by": "vectorweight"
                }
            }
        }
        
        with open(infra_dir / "namespace.yaml", 'w') as f:
            yaml.dump(namespace_manifest, f, default_flow_style=False)
        
        # Generate basic ingress if needed
        if cluster.size.value != "minimal":
            self._generate_ingress_config(cluster, infra_dir)
    
    def _generate_ingress_config(self, cluster: ClusterConfiguration, infra_dir: Path) -> None:
        """Generate basic ingress configuration"""
        ingress_manifest = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f"{cluster.name}-ingress",
                "namespace": f"{cluster.name}-system",
                "annotations": {
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "cert-manager.io/cluster-issuer": "letsencrypt-prod"
                }
            },
            "spec": {
                "tls": [
                    {
                        "hosts": [cluster.domain],
                        "secretName": f"{cluster.name}-tls"
                    }
                ],
                "rules": [
                    {
                        "host": cluster.domain,
                        "http": {
                            "paths": [
                                {
                                    "path": "/",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": f"{cluster.name}-app",
                                            "port": {"number": 80}
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        with open(infra_dir / "ingress.yaml", 'w') as f:
            yaml.dump(ingress_manifest, f, default_flow_style=False)
    
    def _generate_deployment_script(self) -> None:
        """Generate deployment script"""
        script_content = f"""#!/bin/bash
# VectorWeight Homelab Deployment Script
# Generated for project: {self.config.project_name}

set -e

echo "🚀 Deploying VectorWeight Homelab: {self.config.project_name}"
echo "Environment: {self.config.environment}"
echo "Clusters: {len(self.config.clusters)}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if ArgoCD is installed
if ! kubectl get namespace argocd &> /dev/null; then
    echo "⚠️  ArgoCD namespace not found. Installing ArgoCD..."
    kubectl create namespace argocd
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
    echo "✅ ArgoCD installed. Waiting for pods to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
fi

# Deploy cluster applications
{self._generate_cluster_deployment_commands()}

echo "✅ VectorWeight Homelab deployment completed!"
echo ""
echo "Next steps:"
echo "1. Configure ArgoCD access:"
echo "   kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "2. Get ArgoCD admin password:"
echo "   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{{.data.password}}' | base64 -d"
echo "3. Access ArgoCD at https://localhost:8080"
echo ""
echo "Cluster endpoints:"
{self._generate_cluster_endpoints()}
"""
        
        script_path = self.output_path / "deploy.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable (Unix-like systems)
        if os.name != 'nt':
            os.chmod(script_path, 0o755)
    
    def _generate_cluster_deployment_commands(self) -> str:
        """Generate deployment commands for each cluster"""
        commands = []
        for cluster in self.config.clusters:
            commands.append(f"""
echo "📦 Deploying cluster: {cluster.name}"
kubectl apply -f {cluster.name}/application.yaml
kubectl apply -f {cluster.name}/infrastructure/""")
        return "\n".join(commands)
    
    def _generate_cluster_endpoints(self) -> str:
        """Generate cluster endpoint information"""
        endpoints = []
        for cluster in self.config.clusters:
            endpoints.append(f'echo "  {cluster.name}: https://{cluster.domain}"')
        return "\n".join(endpoints)
    
    def _generate_readme(self) -> None:
        """Generate deployment README"""
        readme_content = f"""# VectorWeight Homelab Deployment

## Project: {self.config.project_name}

**Environment:** {self.config.environment}  
**Deployment Mode:** {self.config.deployment_mode.value}  
**Base Domain:** {self.config.base_domain}

## Clusters

{self._generate_cluster_table()}

## Quick Start

1. **Deploy the infrastructure:**
   ```bash
   ./deploy.sh
   ```

2. **Access ArgoCD:**
   ```bash
   kubectl port-forward svc/argocd-server -n argocd 8080:443
   ```

3. **Get admin password:**
   ```bash
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{{.data.password}}' | base64 -d
   ```

## Structure

```
{self._generate_structure_tree()}
```

## Generated Files

- `deploy.sh` - Main deployment script
- `<cluster>/application.yaml` - ArgoCD application manifests
- `<cluster>/infrastructure/` - Cluster infrastructure manifests

---
*Generated by VectorWeight Homelab v0.1.0*
"""
        
        with open(self.output_path / "README.md", 'w') as f:
            f.write(readme_content)
    
    def _generate_cluster_table(self) -> str:
        """Generate markdown table of clusters"""
        table = "| Name | Domain | Size | GPU |\n|------|--------|------|-----|\n"
        for cluster in self.config.clusters:
            gpu_status = "✅" if cluster.gpu_enabled else "❌"
            table += f"| {cluster.name} | {cluster.domain} | {cluster.size.value} | {gpu_status} |\n"
        return table
    
    def _generate_structure_tree(self) -> str:
        """Generate file structure tree"""
        tree = f"{self.config.project_name}-deployment/\n"
        tree += "├── deploy.sh\n"
        tree += "├── README.md\n"
        
        for i, cluster in enumerate(self.config.clusters):
            is_last = i == len(self.config.clusters) - 1
            prefix = "└──" if is_last else "├──"
            tree += f"{prefix} {cluster.name}/\n"
            
            subprefix = "    " if is_last else "│   "
            tree += f"{subprefix}├── application.yaml\n"
            tree += f"{subprefix}└── infrastructure/\n"
            tree += f"{subprefix}    ├── namespace.yaml\n"
            if cluster.size.value != "minimal":
                tree += f"{subprefix}    └── ingress.yaml\n"
        
        return tree
