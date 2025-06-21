#!/usr/bin/env python3
"""
VectorWeight Utility Modules
Exception handling, logging configuration, and project constants
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum


# =============================================================================
# EXCEPTIONS MODULE (vectorweight/utils/exceptions.py)
# =============================================================================

class VectorWeightError(Exception):
    """Base exception for VectorWeight operations"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(VectorWeightError):
    """Raised when configuration is invalid or incomplete"""
    pass


class ValidationError(VectorWeightError):
    """Raised when validation fails"""
    pass


class SourceError(VectorWeightError):
    """Raised when source operations fail"""
    pass


class GitHubAPIError(VectorWeightError):
    """Raised when GitHub API operations fail"""
    pass


class DeploymentError(VectorWeightError):
    """Raised when deployment operations fail"""
    pass


class IntegrationError(VectorWeightError):
    """Raised when integration setup fails"""
    pass


# =============================================================================
# LOGGING MODULE (vectorweight/utils/logging.py)
# =============================================================================

class ColoredFormatter(logging.Formatter):
    """Colored log formatter for better terminal output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging(level: int = logging.INFO, 
                 log_file: Optional[Path] = None,
                 enable_colors: bool = True) -> None:
    """
    Setup logging configuration for VectorWeight
    
    Args:
        level: Logging level
        log_file: Optional log file path
        enable_colors: Enable colored output for terminal
    """
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger
    root_logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if enable_colors and hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress verbose third-party logging
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('github').setLevel(logging.WARNING)
    logging.getLogger('git').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


# =============================================================================
# CONSTANTS MODULE (vectorweight/utils/constants.py)
# =============================================================================

class ProjectConstants:
    """VectorWeight project constants"""
    
    # Project metadata
    PROJECT_NAME = "VectorWeight Homelab"
    PROJECT_VERSION = "2.0.0"
    PROJECT_DESCRIPTION = "Kubernetes GitOps automation for AI/ML homelabs"
    
    # Default configuration values
    DEFAULT_NAMESPACE = "default"
    DEFAULT_STORAGE_CLASS = "openebs-hostpath"
    DEFAULT_METALLB_IP_RANGE = "192.168.1.200-192.168.1.250"
    DEFAULT_BASE_DOMAIN = "vectorweight.com"
    DEFAULT_GITHUB_ORG = "vectorweight"
    
    # Helm chart versions
    HELM_CHART_VERSIONS = {
        "cilium": "1.17.4",
        "metallb": "6.4.18",
        "istio-base": "1.26.1",
        "istio-istiod": "1.26.1",
        "prometheus": "61.3.2",
        "argo-cd": "8.1.1",
        "weaviate": "25.2.3",
        "qdrant": "0.7.0",
        "cerbos": "0.30.0",
        "gpu-operator": "v23.6.1",
        "openebs": "4.2.0"
    }
    
    # Helm repositories
    HELM_REPOSITORIES = {
        "cilium": "https://helm.cilium.io/",
        "metallb": "oci://registry-1.docker.io/bitnamicharts",
        "istio": "https://istio-release.storage.googleapis.com/charts",
        "prometheus": "https://prometheus-community.github.io/helm-charts",
        "argo": "https://argoproj.github.io/argo-helm",
        "bitnami": "https://charts.bitnami.com/bitnami",
        "jetstack": "https://charts.jetstack.io",
        "weaviate": "https://weaviate.github.io/weaviate-helm",
        "qdrant": "https://qdrant.github.io/qdrant-helm",
        "cerbos": "https://cerbos.dev/helm-charts",
        "nvidia": "https://helm.ngc.nvidia.com/nvidia",
        "openebs": "https://openebs.github.io/openebs"
    }
    
    # Container images
    CONTAINER_IMAGES = {
        "weaviate": "semitechnologies/weaviate:1.24.0",
        "qdrant": "qdrant/qdrant:v1.7.0",
        "chroma": "chromadb/chroma:0.4.15",
        "cerbos": "ghcr.io/cerbos/cerbos:0.30.0",
        "postgres": "postgres:15.3",
        "mongodb": "mongo:6.0.8"
    }
    
    # Resource requirements by cluster size
    CLUSTER_SIZE_RESOURCES = {
        "minimal": {
            "cpu_cores": 2,
            "memory_gb": 4,
            "storage_gb": 50,
            "max_pods": 50
        },
        "small": {
            "cpu_cores": 4,
            "memory_gb": 8,
            "storage_gb": 100,
            "max_pods": 100
        },
        "medium": {
            "cpu_cores": 8,
            "memory_gb": 16,
            "storage_gb": 250,
            "max_pods": 200
        },
        "large": {
            "cpu_cores": 16,
            "memory_gb": 32,
            "storage_gb": 500,
            "max_pods": 500
        }
    }
    
    # Network configuration
    NETWORK_CONFIGS = {
        "pod_cidr": "10.244.0.0/16",
        "service_cidr": "10.96.0.0/12",
        "cluster_dns": "10.96.0.10",
        "max_pods_per_node": 110
    }
    
    # Security defaults
    SECURITY_DEFAULTS = {
        "enable_network_policies": True,
        "enable_pod_security_standards": True,
        "enable_rbac": True,
        "enable_admission_controllers": True,
        "default_security_context": {
            "runAsNonRoot": True,
            "runAsUser": 65534,
            "runAsGroup": 65534,
            "fsGroup": 65534,
            "seccompProfile": {"type": "RuntimeDefault"}
        }
    }
    
    # File paths and naming
    STATE_FILE_NAME = "deployment_state.json"
    CONFIG_FILE_EXTENSIONS = [".yaml", ".yml", ".json"]
    BACKUP_FILE_SUFFIX = ".backup"
    
    # API endpoints and timeouts
    GITHUB_API_BASE = "https://api.github.com"
    DEFAULT_TIMEOUT = 30
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5
    
    # Monitoring and observability
    MONITORING_DEFAULTS = {
        "metrics_retention": "30d",
        "log_retention": "14d",
        "scrape_interval": "15s",
        "evaluation_interval": "15s"
    }


class ClusterRole(Enum):
    """Predefined cluster roles and their characteristics"""
    
    DEVELOPMENT = {
        "name": "development",
        "description": "Development and testing workloads",
        "default_size": "small",
        "gpu_required": False,
        "vector_store_recommended": False,
        "cerbos_required": False,
        "workloads": ["development", "testing", "ci-cd"]
    }
    
    AI_ML = {
        "name": "ai-ml",
        "description": "AI/ML training and inference workloads",
        "default_size": "large",
        "gpu_required": True,
        "vector_store_recommended": True,
        "cerbos_required": True,
        "workloads": ["machine-learning", "ai-inference", "model-training"]
    }
    
    GENERAL_PURPOSE = {
        "name": "general-purpose",
        "description": "General application hosting",
        "default_size": "medium",
        "gpu_required": False,
        "vector_store_recommended": False,
        "cerbos_required": False,
        "workloads": ["web-services", "applications", "databases"]
    }
    
    SECURITY = {
        "name": "security",
        "description": "Security monitoring and operations",
        "default_size": "small",
        "gpu_required": False,
        "vector_store_recommended": False,
        "cerbos_required": True,
        "workloads": ["security", "monitoring", "audit", "compliance"]
    }


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_domain_name(domain: str) -> bool:
    """Validate domain name format"""
    import re
    
    pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
    return re.match(pattern, domain) is not None


def validate_ip_range(ip_range: str) -> bool:
    """Validate IP range format (e.g., 192.168.1.200-192.168.1.250)"""
    import ipaddress
    
    try:
        if '-' not in ip_range:
            return False
        
        start_ip, end_ip = ip_range.split('-', 1)
        start_addr = ipaddress.ip_address(start_ip.strip())
        end_addr = ipaddress.ip_address(end_ip.strip())
        
        return start_addr < end_addr
    except (ValueError, ipaddress.AddressValueError):
        return False


def validate_kubernetes_name(name: str) -> bool:
    """Validate Kubernetes resource name format"""
    import re
    
    # Kubernetes names must be lowercase alphanumeric with hyphens
    pattern = r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
    return (
        re.match(pattern, name) is not None and
        len(name) <= 253 and
        not name.startswith('-') and
        not name.endswith('-')
    )


def validate_github_organization(org: str) -> bool:
    """Validate GitHub organization name format"""
    import re
    
    # GitHub usernames/orgs can contain alphanumeric characters and hyphens
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?$'
    return re.match(pattern, org) is not None


# =============================================================================
# RESOURCE CALCULATION UTILITIES
# =============================================================================

def calculate_cluster_resources(cluster_size: str, node_count: int = None) -> Dict[str, Any]:
    """Calculate total cluster resources based on size and node count"""
    
    base_resources = ProjectConstants.CLUSTER_SIZE_RESOURCES.get(cluster_size, 
                                                                ProjectConstants.CLUSTER_SIZE_RESOURCES["small"])
    
    if node_count is None:
        node_count = {
            "minimal": 1,
            "small": 2,
            "medium": 3,
            "large": 5
        }.get(cluster_size, 2)
    
    return {
        "nodes": node_count,
        "total_cpu_cores": base_resources["cpu_cores"] * node_count,
        "total_memory_gb": base_resources["memory_gb"] * node_count,
        "total_storage_gb": base_resources["storage_gb"] * node_count,
        "max_pods": base_resources["max_pods"] * node_count,
        "per_node": base_resources
    }


def estimate_resource_usage(components: List[str], cluster_size: str) -> Dict[str, Any]:
    """Estimate resource usage for given components"""
    
    # Component resource estimates (CPU in millicores, Memory in Mi)
    component_resources = {
        "cilium": {"cpu": 100, "memory": 128},
        "metallb": {"cpu": 50, "memory": 64},
        "istio": {"cpu": 200, "memory": 256},
        "prometheus": {"cpu": 500, "memory": 1024},
        "grafana": {"cpu": 100, "memory": 128},
        "weaviate": {"cpu": 1000, "memory": 2048},
        "qdrant": {"cpu": 500, "memory": 1024},
        "cerbos": {"cpu": 100, "memory": 256},
        "argocd": {"cpu": 200, "memory": 512}
    }
    
    total_cpu = 0
    total_memory = 0
    
    for component in components:
        if component in component_resources:
            total_cpu += component_resources[component]["cpu"]
            total_memory += component_resources[component]["memory"]
    
    cluster_resources = calculate_cluster_resources(cluster_size)
    total_cluster_cpu = cluster_resources["total_cpu_cores"] * 1000  # Convert to millicores
    total_cluster_memory = cluster_resources["total_memory_gb"] * 1024  # Convert to Mi
    
    return {
        "estimated_cpu_usage": total_cpu,
        "estimated_memory_usage": total_memory,
        "cpu_utilization_percent": (total_cpu / total_cluster_cpu) * 100,
        "memory_utilization_percent": (total_memory / total_cluster_memory) * 100,
        "cluster_capacity": {
            "cpu_millicores": total_cluster_cpu,
            "memory_mi": total_cluster_memory
        }
    }


# =============================================================================
# FILE AND PATH UTILITIES
# =============================================================================

def ensure_directory(path: Path) -> Path:
    """Ensure directory exists, create if necessary"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def backup_file(file_path: Path) -> Path:
    """Create backup of existing file"""
    if file_path.exists():
        backup_path = file_path.with_suffix(f"{file_path.suffix}{ProjectConstants.BACKUP_FILE_SUFFIX}")
        backup_path.write_bytes(file_path.read_bytes())
        return backup_path
    return file_path


def find_config_file(search_paths: List[Path], config_names: List[str]) -> Optional[Path]:
    """Find configuration file in search paths"""
    for search_path in search_paths:
        if search_path.is_file():
            return search_path
        
        if search_path.is_dir():
            for config_name in config_names:
                for ext in ProjectConstants.CONFIG_FILE_EXTENSIONS:
                    config_file = search_path / f"{config_name}{ext}"
                    if config_file.exists():
                        return config_file
    
    return None


# =============================================================================
# ENVIRONMENT UTILITIES
# =============================================================================

def load_environment_variables(prefix: str = "VECTORWEIGHT_") -> Dict[str, str]:
    """Load environment variables with specified prefix"""
    import os
    
    env_vars = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            clean_key = key[len(prefix):].lower()
            env_vars[clean_key] = value
    
    return env_vars


def check_required_tools() -> Dict[str, bool]:
    """Check if required external tools are available"""
    import shutil
    
    required_tools = {
        "kubectl": "Kubernetes CLI",
        "helm": "Helm package manager",
        "git": "Git version control",
        "docker": "Docker container runtime"
    }
    
    tool_status = {}
    for tool, description in required_tools.items():
        tool_status[tool] = shutil.which(tool) is not None
    
    return tool_status


def get_system_info() -> Dict[str, Any]:
    """Get system information for deployment planning"""
    import platform
    import psutil
    
    return {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
    }
