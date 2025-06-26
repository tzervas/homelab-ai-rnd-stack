#!/usr/bin/env python3
"""Configuration loader for VectorWeight Homelab.

This module provides functionality for loading, validating, and managing
configuration for VectorWeight Homelab deployments. It supports various
configuration sources including YAML files, environment variables, and
command-line arguments.

The loader handles configuration inheritance, validation, and provides
a unified interface for accessing configuration values throughout the
application.

Typical usage example:
    ```python
    from vectorweight.config.loader import ConfigLoader
    from vectorweight.config.schema import VectorWaveConfig

    loader = ConfigLoader()
    config = loader.load("config.yaml")
    
    # Access configuration
    print(f"Deploying to {config.clusters[0].domain}")
    ```
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast
import yaml
from dataclasses import asdict
from .schema import (
    VectorWaveConfig,
    ClusterConfig,
    SourceConfig,
    DeploymentMode,
    ClusterSize,
    VectorStoreType,
)

class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass

class ConfigLoader:
    """Configuration loader for VectorWeight Homelab.
    
    This class handles loading configuration from various sources,
    validating it against the schema, and providing access to
    configuration values.
    
    Attributes:
        config: The loaded and validated configuration
        env_prefix: Prefix for environment variables
        config_paths: List of paths to search for config files
    """
    
    def __init__(
        self,
        env_prefix: str = "VECTORWEIGHT_",
        config_paths: Optional[List[Path]] = None
    ) -> None:
        """Initialize the configuration loader.
        
        Args:
            env_prefix: Prefix for environment variables (default: VECTORWEIGHT_)
            config_paths: List of paths to search for config files
                If not provided, defaults to standard locations:
                - ./config
                - ~/.config/vectorweight
                - /etc/vectorweight
        
        Raises:
            ValueError: If config_paths contains invalid paths
        """
        self.env_prefix = env_prefix
        self.config_paths = config_paths or [
            Path("./config"),
            Path.home() / ".config" / "vectorweight",
            Path("/etc/vectorweight"),
        ]
        self.config: Optional[VectorWaveConfig] = None
        
        # Validate config paths
        for path in self.config_paths:
            if path.exists() and not path.is_dir():
                raise ValueError(f"Config path {path} exists but is not a directory")
    
    def load(self, config_file: Union[str, Path]) -> VectorWaveConfig:
        """Load configuration from a file.
        
        Args:
            config_file: Path to the configuration file
                Can be absolute or relative to config_paths
        
        Returns:
            The loaded and validated configuration
        
        Raises:
            FileNotFoundError: If config file cannot be found
            ConfigValidationError: If configuration is invalid
            yaml.YAMLError: If config file contains invalid YAML
        """
        # Find config file
        config_path = self._find_config_file(config_file)
        if not config_path:
            raise FileNotFoundError(f"Config file {config_file} not found")
            
        # Load YAML
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
            
        # Apply environment variables
        config_dict = self._apply_env_vars(config_dict)
        
        # Convert to config object
        try:
            config = self._dict_to_config(config_dict)
        except (ValueError, TypeError) as e:
            raise ConfigValidationError(f"Invalid configuration: {e}")
            
        # Validate configuration
        self._validate_config(config)
        
        self.config = config
        return config
    
    def _find_config_file(self, config_file: Union[str, Path]) -> Optional[Path]:
        """Find configuration file in search paths.
        
        Args:
            config_file: Configuration file name or path
        
        Returns:
            Path to config file if found, None otherwise
        """
        config_path = Path(config_file)
        
        # Check absolute path
        if config_path.is_absolute() and config_path.is_file():
            return config_path
            
        # Search in config paths
        for path in self.config_paths:
            full_path = path / config_path
            if full_path.is_file():
                return full_path
                
        return None
    
    def _apply_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration.
        
        Environment variables should be prefixed with env_prefix and use
        double underscores as separators. For example:
        VECTORWEIGHT_DOMAIN="example.com"
        VECTORWEIGHT_CLUSTERS__0__NAME="dev"
        
        Args:
            config: Configuration dictionary to update
        
        Returns:
            Updated configuration dictionary
        """
        for key, value in os.environ.items():
            if not key.startswith(self.env_prefix):
                continue
                
            # Remove prefix and split into parts
            config_key = key[len(self.env_prefix):].lower()
            parts = config_key.split("__")
            
            # Update nested dictionary
            current = config
            for part in parts[:-1]:
                if part.isdigit():
                    part = int(part)
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set value
            current[parts[-1]] = value
            
        return config
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> VectorWaveConfig:
        """Convert configuration dictionary to VectorWaveConfig object.
        
        Args:
            config_dict: Configuration dictionary
        
        Returns:
            VectorWaveConfig object
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Convert enums
        if "deployment_mode" in config_dict:
            config_dict["deployment_mode"] = DeploymentMode(config_dict["deployment_mode"])
        if "cluster_size_default" in config_dict:
            config_dict["cluster_size_default"] = ClusterSize(config_dict["cluster_size_default"])
        if "vector_store_default" in config_dict:
            config_dict["vector_store_default"] = VectorStoreType(config_dict["vector_store_default"])
            
        # Convert clusters
        if "clusters" in config_dict:
            clusters = []
            for cluster in config_dict["clusters"]:
                if "size" in cluster:
                    cluster["size"] = ClusterSize(cluster["size"])
                if "vector_store" in cluster:
                    cluster["vector_store"] = VectorStoreType(cluster["vector_store"])
                clusters.append(ClusterConfig(**cluster))
            config_dict["clusters"] = clusters
            
        # Convert source config
        if "source" in config_dict and config_dict["source"]:
            source = config_dict["source"]
            if "type" in source:
                source["type"] = DeploymentMode(source["type"])
            if "path" in source and source["path"]:
                source["path"] = Path(source["path"])
            if "ca_cert" in source and source["ca_cert"]:
                source["ca_cert"] = Path(source["ca_cert"])
            config_dict["source"] = SourceConfig(**source)
            
        return VectorWaveConfig(**config_dict)
    
    def _validate_config(self, config: VectorWaveConfig) -> None:
        """Validate the configuration.
        
        Performs additional validation beyond basic type checking:
        - Ensures cluster names are unique
        - Validates IP address ranges
        - Checks for required fields based on deployment mode
        
        Args:
            config: Configuration to validate
        
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        # Check for unique cluster names
        cluster_names = [c.name for c in config.clusters]
        if len(cluster_names) != len(set(cluster_names)):
            raise ConfigValidationError("Cluster names must be unique")
            
        # Validate IP ranges
        try:
            # Simple format check, could be enhanced
            for octet in config.ip_pool_start.split("."):
                if not 0 <= int(octet) <= 255:
                    raise ValueError
            for octet in config.ip_pool_end.split("."):
                if not 0 <= int(octet) <= 255:
                    raise ValueError
        except ValueError:
            raise ConfigValidationError("Invalid IP address format")
            
        # Check airgapped requirements
        if config.deployment_mode != DeploymentMode.INTERNET:
            if not config.source:
                raise ConfigValidationError("Source configuration required for air-gapped deployment")
            if config.source.type != config.deployment_mode:
                raise ConfigValidationError("Source type must match deployment mode")
                
        # Validate based on cluster size
        for cluster in config.clusters:
            if cluster.size == ClusterSize.MINIMAL and cluster.specialized_workloads:
                raise ConfigValidationError("Specialized workloads not supported in minimal clusters")
