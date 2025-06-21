#!/usr/bin/env python3
"""
Enhanced VectorWeight Homelab Generator
Idempotent, comprehensive deployment automation with airgapped support
"""

import os
import yaml
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import asdict
import requests
import tarfile
import zipfile
import git
from urllib.parse import urlparse

from enhanced_config_schema import (
    VectorWaveConfig, DeploymentMode, ClusterSize, VectorStoreType,
    SourceConfig, ClusterConfig
)

class SourceManager:
    """Manages different source types for airgapped deployments"""
    
    def __init__(self, source_config: SourceConfig, temp_dir: Path):
        self.config = source_config
        self.temp_dir = temp_dir
        self.local_path = temp_dir / "sources"
        self.local_path.mkdir(exist_ok=True)
    
    def fetch_sources(self) -> Path:
        """Fetch sources based on configuration"""
        if self.config.type == DeploymentMode.INTERNET:
            return self._fetch_internet_sources()
        elif self.config.type == DeploymentMode.AIRGAPPED_VC:
            return self._fetch_vc_sources()
        elif self.config.type == DeploymentMode.AIRGAPPED_LOCAL:
            return self._copy_local_sources()
        elif self.config.type == DeploymentMode.AIRGAPPED_NETWORK:
            return self._fetch_network_sources()
        elif self.config.type == DeploymentMode.AIRGAPPED_ARCHIVE:
            return self._extract_archive_sources()
        else:
            raise ValueError(f"Unsupported deployment mode: {self.config.type}")
    
    def _fetch_internet_sources(self) -> Path:
        """Use standard internet-based sources"""
        return self.local_path
    
    def _fetch_vc_sources(self) -> Path:
        """Clone from version control"""
        repo_path = self.local_path / "repositories"
        if self.config.url:
            git.Repo.clone_from(
                self.config.url,
                repo_path,
                env={
                    "GIT_USERNAME": self.config.username or "",
                    "GIT_PASSWORD": self.config.token or self.config.password or ""
                }
            )
        return repo_path
    
    def _copy_local_sources(self) -> Path:
        """Copy from local directory"""
        if self.config.path and self.config.path.exists():
            shutil.copytree(self.config.path, self.local_path / "local", dirs_exist_ok=True)
        return self.local_path / "local"
    
    def _fetch_network_sources(self) -> Path:
        """Fetch from network location"""
        # Implementation for network file systems, HTTP endpoints, etc.
        network_path = self.local_path / "network"
        network_path.mkdir(exist_ok=True)
        
        if self.config.url:
            # Handle HTTP/HTTPS downloads
            if self.config.url.startswith(('http://', 'https://')):
                self._download_from_http(self.config.url, network_path)
            # Handle SMB/NFS/SSH mounts
            else:
                self._mount_network_path(self.config.url, network_path)
        
        return network_path
    
    def _extract_archive_sources(self) -> Path:
        """Extract from archive files"""
        archive_path = self.local_path / "archive"
        archive_path.mkdir(exist_ok=True)
        
        if self.config.path and self.config.path.exists():
            self._extract_archive(self.config.path, archive_path)
        elif self.config.url:
            # Download and extract
            downloaded_archive = self._download_archive(self.config.url)
            self._extract_archive(downloaded_archive, archive_path)
        
        return archive_path
    
    def _extract_archive(self, archive_file: Path, extract_to: Path):
        """Extract various archive formats"""
        if archive_file.suffix in ['.tar', '.tar.gz', '.tgz']:
            with tarfile.open(archive_file) as tar:
                tar.extractall(extract_to)
        elif archive_file.suffix == '.zip':
            with zipfile.ZipFile(archive_file) as zip_file:
                zip_file.extractall(extract_to)
        else:
            raise ValueError(f"Unsupported archive format: {archive_file.suffix}")

class CerbosIntegration:
    """Handles Cerbos authorization engine integration"""
    
    @staticmethod
    def generate_cerbos_config(clusters: List[ClusterConfig]) -> Dict:
        """Generate Cerbos configuration"""
        return {
            "cerbos": {
                "enabled": True,
                "deployment_mode": "cluster",
                "replicas": 3,
                "namespace": "authorization",
                "policy_repository": "https://github.com/vectorweight/cerbos-policies",
                "audit_enabled": True,
                "postgres_enabled": True,
                "postgres_config": {
                    "host": "cerbos-postgres.authorization.svc.cluster.local",
                    "database": "cerbos",
                    "username": "${CERBOS_DB_USERNAME}",
                    "password": "${CERBOS_DB_PASSWORD}"
                },
                "jwt_verification": {
                    "enabled": True,
                    "issuers": [
                        {
                            "issuer": "https://auth.vectorweight.com",
                            "audience": "vectorweight-services"
                        }
                    ]
                }
            }
        }

class VectorStoreManager:
    """Manages vector store configurations"""
    
    @staticmethod
    def generate_vector_store_config(store_type: VectorStoreType, cluster_config: ClusterConfig) -> Dict:
        """Generate vector store configuration"""
        if store_type == VectorStoreType.DISABLED:
            return {}
        
        base_config = {
            "enabled": True,
            "namespace": "vector-stores",
            "authentication_enabled": True,
            "encryption_enabled": True,
            "monitoring_enabled": True
        }
        
        if store_type == VectorStoreType.WEAVIATE:
            return {
                **base_config,
                "weaviate": {
                    "provider": "weaviate",
                    "replicas": 3 if cluster_config.size != ClusterSize.MINIMAL else 1,
                    "storage_size": "500Gi",
                    "memory_allocation": "32Gi",
                    "config": {
                        "vectorizer_module": "text2vec-transformers",
                        "enable_modules": [
                            "text2vec-transformers",
                            "qna-transformers"
                        ]
                    }
                }
            }
        elif store_type == VectorStoreType.IN_MEMORY:
            return {
                **base_config,
                "chroma": {
                    "provider": "chroma",
                    "deployment_mode": "in-memory",
                    "replicas": 1,
                    "use_case": "rapid-prototyping"
                }
            }
        # Add other vector store types as needed
        
        return base_config

class EnhancedHelmManager:
    """Enhanced Helm repository and chart management"""
    
    def __init__(self, source_manager: SourceManager):
        self.source_manager = source_manager
        self.repositories = self._init_repositories()
        
    def _init_repositories(self) -> Dict:
        """Initialize repositories based on deployment mode"""
        if self.source_manager.config.type == DeploymentMode.INTERNET:
            return self._get_internet_repositories()
        else:
            return self._get_local_repositories()
    
    def _get_internet_repositories(self) -> Dict:
        """Standard internet-based repositories"""
        return {
            "cilium": {"url": "https://helm.cilium.io/"},
            "metallb": {"url": "oci://registry-1.docker.io/bitnamicharts"},
            "istio": {"url": "https://istio-release.storage.googleapis.com/charts"},
            "prometheus": {"url": "https://prometheus-community.github.io/helm-charts"},
            "argo": {"url": "https://argoproj.github.io/argo-helm"},
            "bitnami": {"url": "https://charts.bitnami.com/bitnami"},
            "weaviate": {"url": "https://weaviate.github.io/weaviate-helm"},
            "cerbos": {"url": "https://cerbos.dev/helm-charts"}
        }
    
    def _get_local_repositories(self) -> Dict:
        """Local/airgapped repositories"""
        sources_path = self.source_manager.local_path
        return {
            "local-charts": {"url": f"file://{sources_path}/charts"},
            "internal-registry": {"url": "registry.vectorweight.internal"}
        }

class EnhancedVectorWeightGenerator:
    """Main enhanced generator with comprehensive automation"""
    
    def __init__(self, config: VectorWaveConfig):
        self.config = config
        self.temp_dir = Path(tempfile.mkdtemp())
        self.source_manager = SourceManager(config.source, self.temp_dir) if config.source else None
        self.helm_manager = EnhancedHelmManager(self.source_manager) if self.source_manager else None
        self.output_path = Path(f"./vectorweight-homelab-{config.environment}")
        
    def generate_all(self) -> None:
        """Generate complete homelab deployment - idempotent"""
        print(f"🚀 Generating VectorWeight Homelab ({self.config.environment})...")
        
        # Create output directory
        self.output_path.mkdir(exist_ok=True)
        
        # Fetch sources if needed
        if self.source_manager:
            print("📥 Fetching deployment sources...")
            self.source_manager.fetch_sources()
        
        # Generate repositories
        if self.config.auto_create_repos:
            self._ensure_repositories_exist()
        
        # Generate cluster configurations
        for cluster in self.config.clusters:
            print(f"📁 Generating {cluster.name}...")
            self._generate_cluster(cluster)
        
        # Generate orchestration
        print("🎯 Generating orchestration...")
        self._generate_orchestration()
        
        # Generate deployment scripts
        self._generate_deployment_scripts()
        
        print(f"✅ Generation complete! Output: {self.output_path.absolute()}")
        self._print_next_steps()
    
    def _ensure_repositories_exist(self):
        """Create GitHub repositories if they don't exist"""
        if not self.config.auto_create_repos:
            return
            
        repos_needed = [f"{self.config.github_org}/{cluster.name}" 
                       for cluster in self.config.clusters]
        repos_needed.append(f"{self.config.github_org}/orchestration-repo")
        
        for repo in repos_needed:
            try:
                # Use GitHub CLI if available
                subprocess.run([
                    "gh", "repo", "create", repo, 
                    "--public", "--description", f"VectorWeight {repo} configuration"
                ], check=True, capture_output=True)
                print(f"✅ Created repository: {repo}")
            except subprocess.CalledProcessError:
                print(f"ℹ️  Repository {repo} already exists or creation failed")
    
    def _generate_cluster(self, cluster: ClusterConfig):
        """Generate individual cluster configuration"""
        cluster_path = self.output_path / cluster.name
        cluster_path.mkdir(exist_ok=True)
        
        # Directory structure
        (cluster_path / "apps").mkdir(exist_ok=True)
        (cluster_path / "infrastructure").mkdir(exist_ok=True)
        (cluster_path / "bootstrap").mkdir(exist_ok=True)
        
        # Generate base infrastructure
        self._generate_base_infrastructure(cluster, cluster_path)
        
        # Generate vector stores if enabled
        if cluster.vector_store != VectorStoreType.DISABLED:
            self._generate_vector_store(cluster, cluster_path)
        
        # Generate Cerbos if enabled
        if cluster.cerbos_enabled or self.config.enable_cerbos:
            self._generate_cerbos_config(cluster, cluster_path)
        
        # Generate applications
        self._generate_cluster_applications(cluster, cluster_path)
        
        # Generate README
        self._generate_cluster_readme(cluster, cluster_path)
    
    def _generate_base_infrastructure(self, cluster: ClusterConfig, cluster_path: Path):
        """Generate base infrastructure components"""
        infra_path = cluster_path / "infrastructure"
        
        # CNI (Cilium)
        cilium_path = infra_path / "cilium"
        cilium_path.mkdir(exist_ok=True)
        
        cilium_values = self._get_cluster_size_values(cluster.size, "cilium")
        if not self.config.use_vms:
            cilium_values.update({
                "hostNetwork": True,
                "kubeProxyReplacement": "strict"
            })
        
        self._write_helm_chart(cilium_path, "cilium", "1.17.4", cilium_values)
        
        # Load Balancer (MetalLB)
        metallb_path = infra_path / "metallb"
        metallb_path.mkdir(exist_ok=True)
        
        metallb_values = {
            "configInline": {
                "address-pools": [{
                    "name": "default",
                    "protocol": "layer2",
                    "addresses": [f"{self.config.ip_pool_start}-{self.config.ip_pool_end}"]
                }]
            }
        }
        
        self._write_helm_chart(metallb_path, "metallb", "6.4.18", metallb_values)
    
    def _generate_vector_store(self, cluster: ClusterConfig, cluster_path: Path):
        """Generate vector store configuration"""
        vs_path = cluster_path / "infrastructure" / "vector-store"
        vs_path.mkdir(exist_ok=True)
        
        vs_config = VectorStoreManager.generate_vector_store_config(
            cluster.vector_store, cluster
        )
        
        # Write vector store Helm chart
        if cluster.vector_store == VectorStoreType.WEAVIATE:
            self._write_helm_chart(vs_path, "weaviate", "25.2.3", vs_config.get("weaviate", {}))
        elif cluster.vector_store == VectorStoreType.IN_MEMORY:
            self._write_helm_chart(vs_path, "chroma", "latest", vs_config.get("chroma", {}))
    
    def _generate_cerbos_config(self, cluster: ClusterConfig, cluster_path: Path):
        """Generate Cerbos authorization configuration"""
        cerbos_path = cluster_path / "infrastructure" / "cerbos"
        cerbos_path.mkdir(exist_ok=True)
        
        cerbos_config = CerbosIntegration.generate_cerbos_config([cluster])
        self._write_helm_chart(cerbos_path, "cerbos", "0.30.0", cerbos_config.get("cerbos", {}))
    
    def _get_cluster_size_values(self, size: ClusterSize, component: str) -> Dict:
        """Get component values based on cluster size"""
        size_configs = {
            ClusterSize.MINIMAL: {"replicas": 1, "resources": {"cpu": "100m", "memory": "128Mi"}},
            ClusterSize.SMALL: {"replicas": 2, "resources": {"cpu": "200m", "memory": "256Mi"}},
            ClusterSize.MEDIUM: {"replicas": 3, "resources": {"cpu": "500m", "memory": "512Mi"}},
            ClusterSize.LARGE: {"replicas": 5, "resources": {"cpu": "1", "memory": "1Gi"}}
        }
        return size_configs.get(size, size_configs[ClusterSize.SMALL])
    
    def _write_helm_chart(self, chart_path: Path, chart_name: str, version: str, values: Dict):
        """Write Helm chart files"""
        # Chart.yaml
        chart_yaml = {
            "apiVersion": "v2",
            "name": chart_path.name,
            "version": "0.1.0",
            "dependencies": [{
                "name": chart_name,
                "version": version,
                "repository": self._get_chart_repository(chart_name)
            }]
        }
        
        with open(chart_path / "Chart.yaml", "w") as f:
            yaml.dump(chart_yaml, f, default_flow_style=False)
        
        # values.yaml
        with open(chart_path / "values.yaml", "w") as f:
            yaml.dump(values, f, default_flow_style=False)
    
    def _get_chart_repository(self, chart_name: str) -> str:
        """Get repository URL for chart"""
        repo_map = {
            "cilium": "https://helm.cilium.io/",
            "metallb": "oci://registry-1.docker.io/bitnamicharts",
            "weaviate": "https://weaviate.github.io/weaviate-helm",
            "cerbos": "https://cerbos.dev/helm-charts"
        }
        return repo_map.get(chart_name, "https://charts.bitnami.com/bitnami")
    
    def _generate_cluster_applications(self, cluster: ClusterConfig, cluster_path: Path):
        """Generate Argo CD Application manifests"""
        # Implementation for generating ArgoCD applications
        pass
    
    def _generate_orchestration(self):
        """Generate orchestration repository"""
        # Implementation for central ArgoCD orchestration
        pass
    
    def _generate_deployment_scripts(self):
        """Generate deployment automation scripts"""
        deploy_script = f"""#!/bin/bash
set -e

echo "🚀 Deploying VectorWeight Homelab ({self.config.environment})..."

# Deployment mode: {self.config.deployment_mode.value}
# Clusters: {', '.join([c.name for c in self.config.clusters])}

# Bootstrap ArgoCD
kubectl apply -f orchestration-repo/bootstrap/

# Deploy ApplicationSets
kubectl apply -f orchestration-repo/applicationsets/

echo "✅ Deployment initiated! Monitor via ArgoCD UI"
"""
        
        script_path = self.output_path / "deploy.sh"
        script_path.write_text(deploy_script)
        script_path.chmod(0o755)
    
    def _generate_cluster_readme(self, cluster: ClusterConfig, cluster_path: Path):
        """Generate cluster-specific README"""
        readme_content = f"""# {cluster.name.title()}

Configuration for {cluster.domain}

## Features
- Size: {cluster.size.value}
- GPU: {'✅' if cluster.gpu_enabled else '❌'}
- Vector Store: {cluster.vector_store.value}
- Cerbos: {'✅' if cluster.cerbos_enabled else '❌'}

## Workloads
{chr(10).join(f'- {w}' for w in cluster.specialized_workloads)}
"""
        
        with open(cluster_path / "README.md", "w") as f:
            f.write(readme_content)
    
    def _print_next_steps(self):
        """Print deployment next steps"""
        print("\n" + "="*60)
        print("🎯 NEXT STEPS:")
        print("="*60)
        print("1. Review generated configurations")
        print("2. Execute deployment script: ./deploy.sh")
        print("3. Monitor via ArgoCD UI")
        print("="*60)

# CLI Interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        with open(config_file) as f:
            config_data = yaml.safe_load(f)
        config = VectorWaveConfig(**config_data)
    else:
        # Use minimal dev example
        from enhanced_config_schema import EXAMPLE_CONFIGS
        config = EXAMPLE_CONFIGS["minimal_dev"]
    
    generator = EnhancedVectorWeightGenerator(config)
    generator.generate_all()
