#!/usr/bin/env python3
"""
VectorWeight Homelab Configuration Schema - Minimal PoC
Simple, focused configuration for basic deployment automation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class DeploymentMode(Enum):
    """Deployment mode options"""
    INTERNET = "internet"
    AIRGAPPED_LOCAL = "airgapped-local"


class ClusterSize(Enum):
    """Cluster deployment size options"""
    MINIMAL = "minimal"      # Single node, basic features
    SMALL = "small"         # 2-3 nodes, standard features
    MEDIUM = "medium"       # 3-5 nodes, full features


@dataclass
class ClusterConfiguration:
    """Simplified cluster configuration"""
    name: str
    domain: str
    size: ClusterSize = ClusterSize.SMALL
    gpu_enabled: bool = False


@dataclass
class VectorWeightConfiguration:
    """Main configuration for VectorWeight Homelab deployment - PoC Version"""
    
    # Core deployment settings
    project_name: str = "vectorweight-homelab"
    environment: str = "development"
    deployment_mode: DeploymentMode = DeploymentMode.INTERNET
    
    # Deployment targets
    clusters: List[ClusterConfiguration] = field(default_factory=list)
    
    # Network configuration
    base_domain: str = "vectorweight.local"
    
    # Minimal required overrides
    custom_values: Dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.clusters:
            # Add default cluster if none specified
            self.clusters.append(
                ClusterConfiguration(
                    name="dev",
                    domain=f"dev.{self.base_domain}",
                    size=ClusterSize.MINIMAL
                )
            )


# Example configurations for PoC
EXAMPLE_CONFIGURATIONS = {
    "minimal_dev": {
        "project_name": "vectorweight-minimal",
        "environment": "development",
        "deployment_mode": "internet",
        "clusters": [
            {
                "name": "dev",
                "domain": "dev.vectorweight.local",
                "size": "minimal"
            }
        ],
        "base_domain": "vectorweight.local"
    },
    
    "small_production": {
        "project_name": "vectorweight-prod",
        "environment": "production", 
        "deployment_mode": "internet",
        "clusters": [
            {
                "name": "main",
                "domain": "vectorweight.local",
                "size": "small"
            }
        ],
        "base_domain": "vectorweight.local"
    }
}
