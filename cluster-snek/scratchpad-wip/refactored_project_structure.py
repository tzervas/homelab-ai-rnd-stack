#!/usr/bin/env python3
"""
VectorWeight Homelab - Refactored Project Structure
Professional-grade Kubernetes GitOps automation with comprehensive deployment modes
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import os
import yaml # type: ignore
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class DeploymentMode(Enum):
    INTERNET = "internet"
    AIRGAPPED_VC = "airgapped-vc"
    AIRGAPPED_LOCAL = "airgapped-local"
    AIRGAPPED_NETWORK = "airgapped-network"
    AIRGAPPED_ARCHIVE = "airgapped-archive"

class ClusterSize(Enum):
    MINIMAL = "minimal"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class VectorStoreType(Enum):
    DISABLED = "disabled"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"
    CHROMA = "chroma"
    CHROMA_MEMORY = "chroma-memory"

class DeploymentTarget(Enum):
    VIRTUAL_MACHINES = "vms"
    DIRECT_HOST = "direct"
    HYBRID = "hybrid"

@dataclass
class UserSettings:
    # Centralized user-configurable variables with good defaults
    project_name: str = "cluster-snek-homelab"
    environment: str = "development"
    deployment_mode: DeploymentMode = DeploymentMode.INTERNET
    deployment_target: DeploymentTarget = DeploymentTarget.VIRTUAL_MACHINES
    base_domain: str = "vectorweight.com"
    metallb_ip_range: str = "192.168.18.200-192.168.18.250"
    sync_policy: str = "automated"
    enable_webhooks: bool = True
    enable_cerbos_global: bool = False
    enable_security_cluster: bool = True
    enable_mcp: bool = False
    enable_gpu_operator: bool = False
    github_token: Optional[str] = None
    auto_create_repositories: bool = True
    global_overrides: Dict[str, Any] = field(default_factory=dict)
    config_file: Optional[Union[str, Path]] = None
    env_file: Optional[Union[str, Path]] = ".env"

def load_env_file(env_path: Union[str, Path]) -> Dict[str, str]:
    """Load environment variables from a .env file."""
    env_vars = {}
    if Path(env_path).exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip()
    return env_vars

def load_user_settings(config_path: Optional[Union[str, Path]] = None,
    env_path: Optional[Union[str, Path]] = ".env") -> UserSettings:
    """
    Load user settings from a configuration file, .env file, and environment variables, applying defaults as needed.

    This function initializes a `UserSettings` object and updates its attributes based on the following sources, in order of precedence:
    1. Configuration file (YAML or JSON) if provided.
    2. .env file (default: ".env").
    3. Environment variables (matching attribute names, case-insensitive).

    Type conversion is handled for boolean and Enum attributes.

    Args:
        config_path (Optional[Union[str, Path]]): Path to a YAML or JSON configuration file. If not provided, this step is skipped.
        env_path (Optional[Union[str, Path]]): Path to a .env file. Defaults to ".env".

    Returns:
        UserSettings: An instance of UserSettings with values loaded from the specified sources.

    Raises:
        ValueError: If the configuration file format is not supported (not YAML or JSON).
    """
    settings = UserSettings()
    # Load from config file if provided
    if config_path and Path(config_path).exists():
        config_path = Path(config_path)
        if config_path.suffix in [".yaml", ".yml"]:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        elif config_path.suffix == ".json":
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        else:
            raise ValueError("Unsupported config file format. Use YAML or JSON.")
        for key, value in config_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
    # Load from .env file
    env_vars = load_env_file(env_path if env_path is not None else ".env")
    for key, value in env_vars.items():
        if hasattr(settings, key):
            attr = getattr(settings, key)
            # Convert to correct type if needed
            if isinstance(attr, bool):
                value = value.lower() in ("1", "true", "yes", "on")
            elif isinstance(attr, Enum):
                value = attr.__class__(value)
            setattr(settings, key, value)
    # Load from environment variables
    for key in vars(settings):
        env_value = os.getenv(key.upper())
        if env_value is not None:
            attr = getattr(settings, key)
            if isinstance(attr, bool):
                env_value = env_value.lower() in ("1", "true", "yes", "on")
            elif isinstance(attr, Enum):
                env_value = attr.__class__(env_value)
            setattr(settings, key, env_value)
    return settings

@dataclass
class SourceConfiguration:
    mode: DeploymentMode
    url: Optional[str] = None
    path: Optional[Path] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    ca_certificate_path: Optional[Path] = None
    verification_enabled: bool = True
    archive_format: str = "tar.gz"

@dataclass
class ClusterConfiguration:
    name: str
    domain: str
    size: ClusterSize = ClusterSize.SMALL
    gpu_enabled: bool = False
    vector_store: VectorStoreType = VectorStoreType.DISABLED
    cerbos_enabled: bool = False
    specialized_workloads: List[str] = field(default_factory=list)
    custom_values: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VectorWaveConfiguration:
    # Now references UserSettings for all user-facing config
    user_settings: UserSettings
    source: Optional[SourceConfiguration] = None
    clusters: List[ClusterConfiguration] = field(default_factory=list)

def load_project_structure(config_path: Optional[Union[str, Path]] = None) -> Dict:
    if config_path is None:
        config_path = Path("project_structure.yaml")
    else:
        config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Project structure file not found: {config_path}")
    if config_path.suffix in [".yaml", ".yml"]:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    elif config_path.suffix == ".json":
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError("Unsupported file format for project structure. Use YAML or JSON.")

def generate_project_structure(base_path: Path, structure: Dict) -> None:
    """
    Generates a project directory and file structure based on a nested dictionary specification.

    Args:
        base_path (Path): The root directory where the project structure will be created.
        structure (Dict): A nested dictionary representing the desired directory and file structure.
            - Keys are directory or file names.
            - Values are either:
                - dict: representing subdirectories/files (for directories)
                - str or None: representing file contents (for files). If the file is a Python file (.py),
                  the content will be wrapped in triple quotes as a docstring.

    Behavior:
        - Creates directories and files recursively as specified in the structure dictionary.
        - For Python files, wraps the content in triple quotes as a docstring.
        - Skips writing files if the content is unchanged.
        - Prints the absolute path to the generated project structure root.

    Example:
        structure = {
            "src": {
                "main.py": "Main entry point",
                "utils.py": "Utility functions"
            },
            "README.md": "# Project Title"
        }
        generate_project_structure(Path("/path/to/project"), structure)
    """
    def create_structure(structure: Dict, current_path: Path) -> None:
        for name, content in structure.items():
            item_path = current_path / name
            if isinstance(content, dict):
                item_path.mkdir(exist_ok=True)
                create_structure(content, item_path)
            else:
                item_path.parent.mkdir(parents=True, exist_ok=True)
                content_to_write = f'"""{content}"""\n' if name.endswith('.py') else (content if content else "")
                if not item_path.exists() or item_path.read_text() != content_to_write:
                    item_path.write_text(content_to_write)
    create_structure(structure, base_path)
    print(f"Project structure generated at: {base_path.absolute()}")

if __name__ == "__main__":
    import sys
    # Load user settings from config file and/or .env
    user_settings = load_user_settings()
    # Load project structure
    PROJECT_STRUCTURE = load_project_structure()
    # Determine target path
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        target_path = Path("./cluster-snek-project")
    # Generate project structure
    generate_project_structure(target_path, PROJECT_STRUCTURE)
