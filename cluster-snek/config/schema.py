#!/usr/bin/env python3
"""
Enhanced VectorWeight Homelab Configuration Schema
Simplified, concise configuration for comprehensive deployment automation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Literal
from pathlib import Path
from enum import Enum

class DeploymentMode(Enum):
    """Deployment mode options"""
    INTERNET = "internet"
    AIRGAPPED_VC = "airgapped-vc" 
    AIRGAPPED_LOCAL = "airgapped-local"
    AIRGAPPED_NETWORK = "airgapped-network"
    AIRGAPPED_ARCHIVE = "airgapped-archive"

class ClusterSize(Enum):
    """Cluster deployment size options"""
    MINIMAL = "minimal"      # Single node, basic features
    SMALL = "small"         # 2-3 nodes, standard features
    MEDIUM = "medium"       # 3-5 nodes, full features
    LARGE = "large"         # 5+ nodes, enterprise features

class VectorStoreType(Enum):
    """Vector store implementation options"""
    DISABLED = "disabled"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant" 
    CHROMA = "chroma"
    IN_MEMORY = "in-memory"

@dataclass
class SourceConfig:
    """Source configuration for airgapped deployments"""
    type: DeploymentMode
    url: Optional[str] = None
    path: Optional[Path] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    ca_cert: Optional[Path] = None
    archive_format: Optional[str] = "tar.gz"
    verification_enabled: bool = True

@dataclass 
class ClusterConfig:
    """Simplified cluster configuration"""
    name: str
    domain: str
    size: ClusterSize = ClusterSize.SMALL
    gpu_enabled: bool = False
    vector_store: VectorStoreType = VectorStoreType.DISABLED
    cerbos_enabled: bool = False
    specialized_workloads: List[str] = field(default_factory=list)
    
@dataclass
class VectorWaveConfig:
    """Main configuration for VectorWeight Homelab deployment"""
    
    # Core deployment settings
    project_name: str = "vectorweight-homelab"
    environment: str = "production"
    deployment_mode: DeploymentMode = DeploymentMode.INTERNET
    
    # Deployment targets
    clusters: List[ClusterConfig] = field(default_factory=list)
    
    # Source configuration for airgapped deployments
    source: Optional[SourceConfig] = None
    
    # Infrastructure options
    use_vms: bool = True  # False = deploy directly on host
    cluster_size_default: ClusterSize = ClusterSize.SMALL
    
    # Security and access
    enable_cerbos: bool = False
    enable_security_cluster: bool = True
    
    # Vector stores and AI/ML
    vector_store_default: VectorStoreType = VectorStoreType.DISABLED
    enable_mcp: bool = False
    enable_adk: bool = False
    
    # GitOps settings
    github_org: str = "vectorweight"
    auto_create_repos: bool = True
    sync_policy: str = "automated"
    
    # Network configuration
    domain: str = "vectorweight.com"
    ip_pool_start: str = "192.168.1.200"
    ip_pool_end: str = "192.168.1.250"
    
    # Minimal required overrides
    overrides: Dict[str, any] = field(default_factory=dict)

# Example configurations
EXAMPLE_CONFIGS = {
    "minimal_dev": VectorWaveConfig(
        clusters=[
            ClusterConfig(
                name="dev",
                domain="dev.vectorweight.com",
                size=ClusterSize.MINIMAL
            )
        ],
        use_vms=False,
        enable_security_cluster=False
    ),
    
    "full_production": VectorWaveConfig(
        clusters=[
            ClusterConfig(
                name="dev-cluster",
                domain="dev.vectorweight.com", 
                size=ClusterSize.SMALL
            ),
            ClusterConfig(
                name="ai-cluster",
                domain="ai.vectorweight.com",
                size=ClusterSize.MEDIUM,
                gpu_enabled=True,
                vector_store=VectorStoreType.WEAVIATE,
                specialized_workloads=["machine-learning", "ai-inference"]
            ),
            ClusterConfig(
                name="homelab-cluster", 
                domain="homelab.vectorweight.com",
                size=ClusterSize.SMALL
            ),
            ClusterConfig(
                name="security-cluster",
                domain="sec.vectorweight.com",
                size=ClusterSize.SMALL,
                specialized_workloads=["security", "monitoring"]
            )
        ],
        enable_cerbos=True,
        enable_mcp=True,
        vector_store_default=VectorStoreType.DISABLED
    ),
    
    "airgapped_enterprise": VectorWaveConfig(
        deployment_mode=DeploymentMode.AIRGAPPED_VC,
        source=SourceConfig(
            type=DeploymentMode.AIRGAPPED_VC,
            url="https://git.internal.vectorweight.com",
            username="${GIT_USERNAME}",
            token="${GIT_TOKEN}"
        ),
        clusters=[
            ClusterConfig(
                name="ai-cluster",
                domain="ai.internal.vectorweight.com",
                size=ClusterSize.LARGE,
                gpu_enabled=True,
                vector_store=VectorStoreType.WEAVIATE,
                cerbos_enabled=True
            )
        ],
        enable_cerbos=True,
        auto_create_repos=False,
        domain="internal.vectorweight.com"
    )
}
