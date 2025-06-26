"""
VectorWeight Homelab - Kubernetes GitOps Automation
====================================================

Enterprise-grade Kubernetes GitOps automation framework for AI/ML homelabs.
"""

__version__ = "0.1.0"
__author__ = "Tyler Zervas"
__email__ = "tyler@vectorweight.com"

from .config.schema import VectorWeightConfiguration
from .generators.deployment import DeploymentGenerator

__all__ = ["VectorWeightConfiguration", "DeploymentGenerator"]
