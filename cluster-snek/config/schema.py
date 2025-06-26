#!/usr/bin/env python3
"""
VectorWeight Homelab Configuration Schema.

This module defines the configuration schema for the VectorWeight Homelab deployment system.
It provides a type-safe, validated configuration structure that supports various deployment
scenarios from minimal development setups to full production environments.

Key Features:
    - Type-safe configuration with dataclasses and enums
    - Support for multiple deployment modes (internet-connected and air-gapped)
    - Flexible cluster sizing and capabilities
    - Integrated vector store configuration
    - Security and access control settings

Typical usage example:
    ```python
    from vectorweight.config.schema import VectorWaveConfig, ClusterConfig, ClusterSize
    
    config = VectorWaveConfig(
        clusters=[ClusterConfig(
            name="dev",
            domain="dev.example.com",
            size=ClusterSize.MINIMAL
        )]
    )
    ```
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Literal
from pathlib import Path
from enum import Enum

class DeploymentMode(Enum):
    """Deployment mode options for VectorWeight Homelab.
    
    Defines the available deployment modes that determine how the system
    will be deployed and how it will access required resources.
    
    Attributes:
        INTERNET: Standard internet-connected deployment with direct access to resources
        AIRGAPPED_VC: Air-gapped deployment using version control for package distribution
        AIRGAPPED_LOCAL: Air-gapped deployment using local filesystem resources
        AIRGAPPED_NETWORK: Air-gapped deployment using internal network resources
        AIRGAPPED_ARCHIVE: Air-gapped deployment using pre-packaged archive files
    """
    INTERNET = "internet"
    AIRGAPPED_VC = "airgapped-vc" 
    AIRGAPPED_LOCAL = "airgapped-local"
    AIRGAPPED_NETWORK = "airgapped-network"
    AIRGAPPED_ARCHIVE = "airgapped-archive"

class ClusterSize(Enum):
    """Cluster deployment size options defining resource allocations and feature sets.
    
    Determines the scale of the deployment and which features are enabled by default.
    Each size option comes with predefined resource allocations and capability sets.
    
    Attributes:
        MINIMAL: Single node deployment with basic features
            - Suitable for development and testing
            - Limited resource allocation
            - Core services only
        
        SMALL: 2-3 node deployment with standard features
            - Suitable for small teams
            - Moderate resource allocation
            - Basic HA configuration
        
        MEDIUM: 3-5 node deployment with full feature set
            - Suitable for development teams
            - Enhanced resource allocation
            - Full HA configuration
        
        LARGE: 5+ node deployment with enterprise features
            - Suitable for organization-wide use
            - Maximum resource allocation
            - Advanced features and integrations
    """
    MINIMAL = "minimal"      # Single node, basic features
    SMALL = "small"         # 2-3 nodes, standard features
    MEDIUM = "medium"       # 3-5 nodes, full features
    LARGE = "large"         # 5+ nodes, enterprise features

class VectorStoreType(Enum):
    """Vector store implementation options for AI/ML workloads.
    
    Defines the available vector store backends that can be used for
    storing and querying vector embeddings in AI/ML workloads.
    
    Attributes:
        DISABLED: No vector store functionality
        WEAVIATE: Weaviate vector database (https://weaviate.io/)
        QDRANT: Qdrant vector database (https://qdrant.tech/)
        CHROMA: ChromaDB vector database (https://www.trychroma.com/)
        IN_MEMORY: Simple in-memory vector store for testing
    """
    DISABLED = "disabled"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant" 
    CHROMA = "chroma"
    IN_MEMORY = "in-memory"

@dataclass
class SourceConfig:
    """Source configuration for air-gapped deployments.
    
    Defines how resources should be accessed in air-gapped environments
    where direct internet access is not available.
    
    Attributes:
        type: The deployment mode determining how resources are accessed
        url: Optional URL for accessing resources (e.g., internal mirror)
        path: Optional filesystem path for local resources
        username: Optional username for authenticated access
        password: Optional password for authenticated access
        token: Optional access token for authenticated access
        ca_cert: Optional CA certificate for SSL/TLS verification
        archive_format: Format for archived resources (default: tar.gz)
        verification_enabled: Whether to verify resource integrity
    """
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
    """Configuration for an individual Kubernetes cluster.
    
    Defines the characteristics and capabilities of a single cluster
    within the VectorWeight Homelab deployment.
    
    Attributes:
        name: Unique identifier for the cluster
        domain: Domain name for cluster ingress
        size: Deployment size determining resources and features
        gpu_enabled: Whether GPU support should be enabled
        vector_store: Vector store implementation to use
        cerbos_enabled: Whether to enable Cerbos authorization
        specialized_workloads: List of special workload types to enable
    """
    name: str
    domain: str
    size: ClusterSize = ClusterSize.SMALL
    gpu_enabled: bool = False
    vector_store: VectorStoreType = VectorStoreType.DISABLED
    cerbos_enabled: bool = False
    specialized_workloads: List[str] = field(default_factory=list)
    
@dataclass
class VectorWaveConfig:
    """Main configuration for VectorWeight Homelab deployment.
    
    Top-level configuration class that defines all aspects of a
    VectorWeight Homelab deployment including clusters, infrastructure,
    security, and feature enablement.
    
    Attributes:
        project_name: Name identifier for the deployment
        environment: Deployment environment (e.g., production, staging)
        deployment_mode: How the system will be deployed
        clusters: List of cluster configurations
        source: Configuration for air-gapped deployments
        use_vms: Whether to deploy on VMs or bare metal
        cluster_size_default: Default size for new clusters
        enable_cerbos: Whether to enable Cerbos authorization
        enable_security_cluster: Whether to deploy security features
        vector_store_default: Default vector store implementation
        enable_mcp: Whether to enable management control plane
        enable_adk: Whether to enable application development kit
        github_org: GitHub organization for GitOps
        auto_create_repos: Whether to automatically create Git repos
        sync_policy: ArgoCD sync policy
        domain: Base domain for the deployment
        ip_pool_start: Start of IP address pool for services
        ip_pool_end: End of IP address pool for services
        overrides: Additional configuration overrides
    """
    
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
