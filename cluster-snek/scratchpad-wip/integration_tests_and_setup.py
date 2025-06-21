#!/usr/bin/env python3
"""
Integration Tests and Project Setup Files
"""

# =============================================================================
# INTEGRATION TESTS (tests/integration/test_deployment.py)
# =============================================================================

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from vectorweight.config.schema import (
    VectorWaveConfiguration, ClusterConfiguration, 
    ClusterSize, VectorStoreType, DeploymentMode
)
from vectorweight.config.loader import ConfigurationLoader
from vectorweight.generators.enhanced import EnhancedVectorWeightGenerator
from vectorweight.integrations.github import GitHubRepositoryManager
from vectorweight.sources.manager import SourceManager


class TestEndToEndDeployment:
    """End-to-end deployment testing"""
    
    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def minimal_config(self):
        """Minimal test configuration"""
        return VectorWaveConfiguration(
            project_name="test-deployment",
            environment="test",
            clusters=[
                ClusterConfiguration(
                    name="test-cluster",
                    domain="test.example.com",
                    size=ClusterSize.MINIMAL
                )
            ],
            auto_create_repositories=False
        )
    
    @pytest.fixture
    def full_config(self):
        """Full featured test configuration"""
        return VectorWaveConfiguration(
            project_name="test-full-deployment",
            environment="test",
            clusters=[
                ClusterConfiguration(
                    name="ai-cluster",
                    domain="ai.test.example.com",
                    size=ClusterSize.MEDIUM,
                    gpu_enabled=True,
                    vector_store=VectorStoreType.WEAVIATE,
                    cerbos_enabled=True,
                    specialized_workloads=["machine-learning"]
                ),
                ClusterConfiguration(
                    name="security-cluster",
                    domain="sec.test.example.com",
                    size=ClusterSize.SMALL,
                    cerbos_enabled=True,
                    specialized_workloads=["security", "monitoring"]
                )
            ],
            enable_cerbos_global=True,
            enable_gpu_operator=True,
            auto_create_repositories=False
        )
    
    def test_minimal_deployment_generation(self, minimal_config, temp_directory):
        """Test minimal deployment generation"""
        generator = EnhancedVectorWeightGenerator(minimal_config)
        generator.output_path = temp_directory / "minimal-deployment"
        
        # Mock GitHub integration
        with patch.object(generator, '_initialize_github_integration'):
            generator.generate_complete_deployment()
        
        # Verify output structure
        assert generator.output_path.exists()
        assert (generator.output_path / "test-cluster").exists()
        assert (generator.output_path / "test-cluster" / "infrastructure").exists()
        assert (generator.output_path / "test-cluster" / "apps").exists()
        assert (generator.output_path / "orchestration-repo").exists()
        assert (generator.output_path / "deploy.sh").exists()
    
    def test_full_deployment_generation(self, full_config, temp_directory):
        """Test full deployment with all features"""
        generator = EnhancedVectorWeightGenerator(full_config)
        generator.output_path = temp_directory / "full-deployment"
        
        # Mock integrations
        with patch.object(generator, '_initialize_github_integration'), \
             patch.object(generator, '_initialize_source_management'):
            generator.generate_complete_deployment()
        
        # Verify AI cluster components
        ai_cluster_path = generator.output_path / "ai-cluster"
        assert ai_cluster_path.exists()
        assert (ai_cluster_path / "infrastructure" / "weaviate").exists()
        assert (ai_cluster_path / "infrastructure" / "cerbos").exists()
        assert (ai_cluster_path / "infrastructure" / "gpu-operator").exists()
        
        # Verify security cluster components
        security_cluster_path = generator.output_path / "security-cluster"
        assert security_cluster_path.exists()
        assert (security_cluster_path / "infrastructure" / "cerbos").exists()
    
    def test_idempotent_generation(self, minimal_config, temp_directory):
        """Test idempotent deployment generation"""
        generator = EnhancedVectorWeightGenerator(minimal_config)
        generator.output_path = temp_directory / "idempotent-test"
        
        with patch.object(generator, '_initialize_github_integration'):
            # First generation
            generator.generate_complete_deployment()
            first_state = generator.state_manager.state.copy()
            
            # Second generation (should detect no changes)
            generator.generate_complete_deployment()
            second_state = generator.state_manager.state.copy()
            
            # States should be identical
            assert first_state["configuration_hash"] == second_state["configuration_hash"]
    
    @patch('vectorweight.integrations.github.Github')
    def test_github_integration(self, mock_github, minimal_config, temp_directory):
        """Test GitHub repository creation"""
        # Mock GitHub API responses
        mock_org = Mock()
        mock_repo = Mock()
        mock_org.create_repo.return_value = mock_repo
        mock_github.return_value.get_organization.return_value = mock_org
        
        generator = EnhancedVectorWeightGenerator(minimal_config)
        generator.configuration.auto_create_repositories = True
        generator.configuration.github_token = "test-token"
        generator.output_path = temp_directory / "github-test"
        
        generator.generate_complete_deployment()
        
        # Verify GitHub API was called
        mock_github.assert_called_with("test-token")


class TestAirgappedDeployment:
    """Test airgapped deployment scenarios"""
    
    @pytest.fixture
    def airgapped_config(self, temp_directory):
        """Airgapped deployment configuration"""
        from vectorweight.config.schema import SourceConfiguration
        
        # Create mock source directory
        source_dir = temp_directory / "mock-source"
        source_dir.mkdir()
        (source_dir / "charts").mkdir()
        (source_dir / "manifests").mkdir()
        
        return VectorWaveConfiguration(
            project_name="test-airgapped",
            environment="test",
            deployment_mode=DeploymentMode.AIRGAPPED_LOCAL,
            source=SourceConfiguration(
                mode=DeploymentMode.AIRGAPPED_LOCAL,
                path=source_dir
            ),
            clusters=[
                ClusterConfiguration(
                    name="airgapped-cluster",
                    domain="airgapped.test.example.com",
                    size=ClusterSize.SMALL
                )
            ],
            auto_create_repositories=False
        )
    
    def test_airgapped_source_management(self, airgapped_config, temp_directory):
        """Test airgapped source management"""
        with SourceManager(temp_directory / "sources") as source_manager:
            metadata = source_manager.fetch_source(airgapped_config.source)
            
            assert metadata.source_type == "local"
            assert metadata.local_path.exists()
    
    def test_airgapped_deployment_generation(self, airgapped_config, temp_directory):
        """Test airgapped deployment generation"""
        generator = EnhancedVectorWeightGenerator(airgapped_config)
        generator.output_path = temp_directory / "airgapped-deployment"
        
        generator.generate_complete_deployment()
        
        # Verify deployment was generated
        assert generator.output_path.exists()
        assert (generator.output_path / "airgapped-cluster").exists()


class TestConfigurationValidation:
    """Test configuration validation"""
    
    def test_valid_configuration_passes_validation(self):
        """Test that valid configuration passes validation"""
        from vectorweight.config.loader import ConfigurationValidator
        
        config = VectorWaveConfiguration(
            clusters=[
                ClusterConfiguration(
                    name="valid-cluster",
                    domain="valid.example.com"
                )
            ]
        )
        
        validator = ConfigurationValidator()
        messages = validator.validate(config)
        
        errors = [msg for msg in messages if msg.startswith("Error:")]
        assert len(errors) == 0
    
    def test_invalid_configuration_fails_validation(self):
        """Test that invalid configuration fails validation"""
        from vectorweight.config.loader import ConfigurationValidator
        
        config = VectorWaveConfiguration(
            clusters=[
                ClusterConfiguration(
                    name="invalid-cluster-name!",  # Invalid characters
                    domain=""  # Empty domain
                )
            ]
        )
        
        validator = ConfigurationValidator()
        messages = validator.validate(config)
        
        errors = [msg for msg in messages if msg.startswith("Error:")]
        assert len(errors) > 0


# =============================================================================
# SETUP.PY
# =============================================================================

setup_py_content = '''#!/usr/bin/env python3
"""
VectorWeight Homelab Setup Configuration
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split("\\n")

setup(
    name="vectorweight-homelab",
    version="2.0.0",
    description="Kubernetes GitOps automation for AI/ML homelabs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="VectorWeight Technologies",
    author_email="dev@vectorweight.com",
    url="https://github.com/vectorweight/homelab",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Systems Administration",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "sphinx>=6.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "myst-parser>=0.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vectorweight=vectorweight.cli.main:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="kubernetes, gitops, homelab, ai, ml, automation, helm, argocd",
    project_urls={
        "Bug Reports": "https://github.com/vectorweight/homelab/issues",
        "Source": "https://github.com/vectorweight/homelab",
        "Documentation": "https://vectorweight.github.io/homelab",
    },
)
'''

# =============================================================================
# PYPROJECT.TOML
# =============================================================================

pyproject_toml_content = '''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "vectorweight-homelab"
version = "2.0.0"
description = "Kubernetes GitOps automation for AI/ML homelabs"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "VectorWeight Technologies", email = "dev@vectorweight.com"}
]
maintainers = [
    {name = "VectorWeight Technologies", email = "dev@vectorweight.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: System :: Systems Administration",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
keywords = ["kubernetes", "gitops", "homelab", "ai", "ml", "automation", "helm", "argocd"]
dependencies = [
    "click>=8.0.0",
    "PyYAML>=6.0",
    "requests>=2.28.0",
    "PyGithub>=1.58.0",
    "GitPython>=3.1.0",
    "dataclasses-json>=0.5.7",
    "psutil>=5.9.0",
    "rich>=13.0.0",
]
requires-python = ">=3.9"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "pre-commit>=3.0.0",
    "isort>=5.12.0",
]
docs = [
    "sphinx>=6.0.0",
    "sphinx-rtd-theme>=1.2.0",
    "myst-parser>=0.18.0",
    "sphinx-autoapi>=2.1.0",
]
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
    "coverage>=7.0.0",
]

[project.urls]
Homepage = "https://github.com/vectorweight/homelab"
Documentation = "https://vectorweight.github.io/homelab"
Repository = "https://github.com/vectorweight/homelab.git"
"Bug Tracker" = "https://github.com/vectorweight/homelab/issues"
Changelog = "https://github.com/vectorweight/homelab/blob/main/CHANGELOG.md"

[project.scripts]
vectorweight = "vectorweight.cli.main:cli"

[tool.setuptools.packages.find]
include = ["vectorweight*"]
exclude = ["tests*"]

[tool.setuptools.package-data]
vectorweight = ["*.yaml", "*.yml", "*.json", "templates/*"]

# Black configuration
[tool.black]
line-length = 100
target-version = ['py39', 'py310', 'py311', 'py312']
include = '\\.pyi?$'
extend-exclude = '''
/(
  # directories
  \\.eggs
  | \\.git
  | \\.hg
  | \\.mypy_cache
  | \\.tox
  | \\.venv
  | build
  | dist
)/
'''

# isort configuration
[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

# mypy configuration
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = [
    "github.*",
    "git.*",
    "yaml.*",
    "psutil.*",
]
ignore_missing_imports = true

# pytest configuration
[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests that take more than a few seconds",
    "github_api: Tests that require GitHub API access",
]

# Coverage configuration
[tool.coverage.run]
source = ["vectorweight"]
omit = [
    "*/tests/*",
    "*/test_*",
    "setup.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]

[tool.coverage.html]
directory = "htmlcov"
'''

# =============================================================================
# REQUIREMENTS.TXT
# =============================================================================

requirements_txt_content = '''# Core dependencies
click>=8.0.0
PyYAML>=6.0
requests>=2.28.0
PyGithub>=1.58.0
GitPython>=3.1.0
dataclasses-json>=0.5.7
psutil>=5.9.0
rich>=13.0.0

# Optional dependencies for enhanced functionality
kubernetes>=24.2.0
pydantic>=1.10.0
jinja2>=3.1.0
'''

# =============================================================================
# UNIT TESTS (tests/unit/test_config.py)
# =============================================================================

unit_test_config_content = '''#!/usr/bin/env python3
"""
Unit tests for configuration management
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from vectorweight.config.schema import (
    VectorWaveConfiguration, ClusterConfiguration, SourceConfiguration,
    DeploymentMode, ClusterSize, VectorStoreType
)
from vectorweight.config.loader import ConfigurationLoader, ConfigurationValidator
from vectorweight.utils.exceptions import ConfigurationError


class TestVectorWaveConfiguration:
    """Test VectorWaveConfiguration class"""
    
    def test_minimal_configuration(self):
        """Test minimal valid configuration"""
        config = VectorWaveConfiguration(
            clusters=[
                ClusterConfiguration(
                    name="test",
                    domain="test.example.com"
                )
            ]
        )
        
        assert config.project_name == "vectorweight-homelab"
        assert config.environment == "production"
        assert len(config.clusters) == 1
        assert config.clusters[0].name == "test"
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        # Valid configuration should not raise errors
        config = VectorWaveConfiguration(
            clusters=[
                ClusterConfiguration(
                    name="valid-cluster",
                    domain="valid.example.com"
                )
            ]
        )
        # Should not raise exception
        
        # Invalid configuration should raise errors
        with pytest.raises(ConfigurationError):
            VectorWaveConfiguration(clusters=[])  # No clusters
    
    def test_environment_variable_application(self):
        """Test environment variable override"""
        import os
        
        # Set environment variable
        os.environ["GITHUB_TOKEN"] = "test-token"
        
        config = VectorWaveConfiguration(
            clusters=[
                ClusterConfiguration(
                    name="test",
                    domain="test.example.com"
                )
            ]
        )
        
        assert config.github_token == "test-token"
        
        # Clean up
        del os.environ["GITHUB_TOKEN"]


class TestConfigurationLoader:
    """Test ConfigurationLoader class"""
    
    def test_load_from_dict(self):
        """Test loading configuration from dictionary"""
        config_data = {
            "project_name": "test-project",
            "clusters": [
                {
                    "name": "test-cluster",
                    "domain": "test.example.com",
                    "size": "small"
                }
            ]
        }
        
        loader = ConfigurationLoader()
        config = loader.load_from_dict(config_data)
        
        assert config.project_name == "test-project"
        assert len(config.clusters) == 1
        assert config.clusters[0].size == ClusterSize.SMALL
    
    def test_save_and_load_file(self):
        """Test saving and loading configuration file"""
        config = VectorWaveConfiguration(
            project_name="file-test",
            clusters=[
                ClusterConfiguration(
                    name="file-cluster",
                    domain="file.example.com"
                )
            ]
        )
        
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            loader = ConfigurationLoader()
            loader.save_to_file(config, temp_path)
            
            loaded_config = loader.load_from_file(temp_path)
            
            assert loaded_config.project_name == "file-test"
            assert len(loaded_config.clusters) == 1
        finally:
            temp_path.unlink()


class TestConfigurationValidator:
    """Test ConfigurationValidator class"""
    
    def test_valid_configuration_validation(self):
        """Test validation of valid configuration"""
        config = VectorWaveConfiguration(
            clusters=[
                ClusterConfiguration(
                    name="valid",
                    domain="valid.example.com"
                )
            ]
        )
        
        validator = ConfigurationValidator()
        messages = validator.validate(config)
        
        errors = [msg for msg in messages if msg.startswith("Error:")]
        assert len(errors) == 0
    
    def test_invalid_domain_validation(self):
        """Test validation of invalid domain"""
        config = VectorWaveConfiguration(
            clusters=[
                ClusterConfiguration(
                    name="test",
                    domain="invalid domain with spaces"
                )
            ]
        )
        
        validator = ConfigurationValidator()
        messages = validator.validate(config)
        
        # Should have validation warnings/errors about domain
        assert len(messages) > 0
'''

# Write all files to demonstrate complete project structure
def generate_complete_project_files():
    """Generate all project files for the refactored VectorWeight project"""
    
    files = {
        "setup.py": setup_py_content,
        "pyproject.toml": pyproject_toml_content,
        "requirements.txt": requirements_txt_content,
        "tests/unit/test_config.py": unit_test_config_content,
        "tests/integration/test_deployment.py": """# Integration test content from above""",
    }
    
    return files

if __name__ == "__main__":
    files = generate_complete_project_files()
    for file_path, content in files.items():
        print(f"=== {file_path} ===")
        print(content[:500] + "..." if len(content) > 500 else content)
        print()
