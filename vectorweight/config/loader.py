#!/usr/bin/env python3
"""
Configuration loader for VectorWeight Homelab - PoC Version
"""

import yaml
from pathlib import Path
from typing import Dict, Any

from .schema import VectorWeightConfiguration, ClusterConfiguration, DeploymentMode, ClusterSize


class ConfigurationLoader:
    """Load and save VectorWeight configurations"""
    
    def load_from_file(self, file_path: Path) -> VectorWeightConfiguration:
        """Load configuration from YAML file"""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return self.load_from_dict(data)
    
    def load_from_dict(self, data: Dict[str, Any]) -> VectorWeightConfiguration:
        """Load configuration from dictionary"""
        # Parse clusters
        clusters = []
        for cluster_data in data.get('clusters', []):
            cluster = ClusterConfiguration(
                name=cluster_data['name'],
                domain=cluster_data['domain'],
                size=ClusterSize(cluster_data.get('size', 'small')),
                gpu_enabled=cluster_data.get('gpu_enabled', False)
            )
            clusters.append(cluster)
        
        # Create main configuration
        config = VectorWeightConfiguration(
            project_name=data.get('project_name', 'vectorweight-homelab'),
            environment=data.get('environment', 'development'),
            deployment_mode=DeploymentMode(data.get('deployment_mode', 'internet')),
            clusters=clusters,
            base_domain=data.get('base_domain', 'vectorweight.local'),
            custom_values=data.get('custom_values', {})
        )
        
        return config
    
    def save_to_file(self, config: VectorWeightConfiguration, file_path: Path) -> None:
        """Save configuration to YAML file"""
        data = self.to_dict(config)
        
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def to_dict(self, config: VectorWeightConfiguration) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        clusters_data = []
        for cluster in config.clusters:
            cluster_dict = {
                'name': cluster.name,
                'domain': cluster.domain,
                'size': cluster.size.value,
                'gpu_enabled': cluster.gpu_enabled
            }
            clusters_data.append(cluster_dict)
        
        return {
            'project_name': config.project_name,
            'environment': config.environment,
            'deployment_mode': config.deployment_mode.value,
            'clusters': clusters_data,
            'base_domain': config.base_domain,
            'custom_values': config.custom_values
        }


class ConfigurationValidator:
    """Validate VectorWeight configurations"""
    
    def validate(self, config: VectorWeightConfiguration) -> List[str]:
        """Validate configuration and return list of validation messages"""
        messages = []
        
        # Validate project name
        if not config.project_name or not config.project_name.strip():
            messages.append("Error: Project name cannot be empty")
        
        # Validate clusters
        if not config.clusters:
            messages.append("Error: At least one cluster must be configured")
        
        cluster_names = set()
        for cluster in config.clusters:
            # Check for duplicate names
            if cluster.name in cluster_names:
                messages.append(f"Error: Duplicate cluster name '{cluster.name}'")
            cluster_names.add(cluster.name)
            
            # Validate cluster name format
            if not cluster.name.replace('-', '').replace('_', '').isalnum():
                messages.append(f"Warning: Cluster name '{cluster.name}' should be alphanumeric with hyphens/underscores only")
            
            # Validate domain
            if not cluster.domain or '.' not in cluster.domain:
                messages.append(f"Error: Invalid domain '{cluster.domain}' for cluster '{cluster.name}'")
        
        # Validate base domain
        if not config.base_domain or '.' not in config.base_domain:
            messages.append("Error: Invalid base domain")
        
        return messages
