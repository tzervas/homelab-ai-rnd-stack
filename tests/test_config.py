#!/usr/bin/env python3
"""Tests for VectorWeight Homelab configuration modules.

This module contains tests for the configuration schema and loader,
ensuring that configuration validation, loading, and environment
variable handling work correctly.
"""

import os
import pytest
from pathlib import Path
import tempfile
import yaml
from vectorweight.config.loader import ConfigLoader, ConfigValidationError
from vectorweight.config.schema import (
    VectorWaveConfig,
    ClusterConfig,
    SourceConfig,
    DeploymentMode,
    ClusterSize,
    VectorStoreType,
)

@pytest.fixture
def example_config() -> dict:
    """Create an example configuration dictionary."""
    return {
        "project_name": "test-project",
        "environment": "development",
        "deployment_mode": "internet",
        "clusters": [
            {
                "name": "dev",
                "domain": "dev.test.local",
                "size": "minimal",
            }
        ],
        "domain": "test.local",
        "ip_pool_start": "192.168.0.200",
        "ip_pool_end": "192.168.0.250",
    }

@pytest.fixture
def config_file(example_config) -> Path:
    """Create a temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(example_config, f)
        return Path(f.name)

def test_load_config(config_file):
    """Test loading configuration from file."""
    loader = ConfigLoader()
    config = loader.load(config_file)
    
    assert isinstance(config, VectorWaveConfig)
    assert config.project_name == "test-project"
    assert config.environment == "development"
    assert config.deployment_mode == DeploymentMode.INTERNET
    assert len(config.clusters) == 1
    assert config.clusters[0].name == "dev"
    assert config.clusters[0].size == ClusterSize.MINIMAL

def test_env_var_override(config_file):
    """Test environment variable overrides."""
    os.environ["VECTORWEIGHT_PROJECT_NAME"] = "env-project"
    os.environ["VECTORWEIGHT_CLUSTERS__0__DOMAIN"] = "env.test.local"
    
    loader = ConfigLoader()
    config = loader.load(config_file)
    
    assert config.project_name == "env-project"
    assert config.clusters[0].domain == "env.test.local"
    
    del os.environ["VECTORWEIGHT_PROJECT_NAME"]
    del os.environ["VECTORWEIGHT_CLUSTERS__0__DOMAIN"]

def test_invalid_ip_range(example_config, config_file):
    """Test validation of IP address ranges."""
    example_config["ip_pool_start"] = "invalid"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(example_config, f)
        invalid_config = Path(f.name)
    
    loader = ConfigLoader()
    with pytest.raises(ConfigValidationError, match="Invalid IP address format"):
        loader.load(invalid_config)

def test_airgapped_validation(example_config, config_file):
    """Test validation of air-gapped deployment configuration."""
    example_config["deployment_mode"] = "airgapped-vc"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(example_config, f)
        invalid_config = Path(f.name)
    
    loader = ConfigLoader()
    with pytest.raises(ConfigValidationError, match="Source configuration required"):
        loader.load(invalid_config)

def test_cluster_name_uniqueness(example_config, config_file):
    """Test validation of unique cluster names."""
    example_config["clusters"].append({
        "name": "dev",  # Duplicate name
        "domain": "dev2.test.local",
        "size": "small",
    })
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(example_config, f)
        invalid_config = Path(f.name)
    
    loader = ConfigLoader()
    with pytest.raises(ConfigValidationError, match="Cluster names must be unique"):
        loader.load(invalid_config)

def test_minimal_cluster_validation(example_config, config_file):
    """Test validation of minimal cluster capabilities."""
    example_config["clusters"][0]["specialized_workloads"] = ["not-allowed"]
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(example_config, f)
        invalid_config = Path(f.name)
    
    loader = ConfigLoader()
    with pytest.raises(ConfigValidationError, match="Specialized workloads not supported"):
        loader.load(invalid_config)

def test_config_search_paths():
    """Test configuration file search path handling."""
    loader = ConfigLoader(config_paths=[Path("/nonexistent")])
    
    with pytest.raises(FileNotFoundError):
        loader.load("config.yaml")

def test_vector_store_conversion(example_config, config_file):
    """Test conversion of vector store configuration."""
    example_config["clusters"][0]["vector_store"] = "weaviate"
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(example_config, f)
        config_file = Path(f.name)
    
    loader = ConfigLoader()
    config = loader.load(config_file)
    
    assert config.clusters[0].vector_store == VectorStoreType.WEAVIATE

def test_source_config_conversion(example_config, config_file):
    """Test conversion of source configuration."""
    example_config["deployment_mode"] = "airgapped-vc"
    example_config["source"] = {
        "type": "airgapped-vc",
        "url": "https://git.internal.test",
        "token": "test-token",
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(example_config, f)
        config_file = Path(f.name)
    
    loader = ConfigLoader()
    config = loader.load(config_file)
    
    assert isinstance(config.source, SourceConfig)
    assert config.source.type == DeploymentMode.AIRGAPPED_VC
    assert config.source.url == "https://git.internal.test"
    assert config.source.token == "test-token"
