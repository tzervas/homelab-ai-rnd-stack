#!/usr/bin/env python3
"""
Vector Store Integration Module
Comprehensive vector database management for AI/ML workloads
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

from vectorweight.config.schema import ClusterConfiguration, VectorStoreType, ClusterSize

logger = logging.getLogger(__name__)


@dataclass
class VectorStoreConfiguration:
    """Vector store deployment configuration"""
    provider: str
    namespace: str
    storage_size: str
    memory_allocation: str
    cpu_allocation: str
    replicas: int
    authentication_enabled: bool
    encryption_enabled: bool
    monitoring_enabled: bool
    backup_enabled: bool


class VectorStoreProvider(ABC):
    """Abstract base class for vector store providers"""
    
    @abstractmethod
    def generate_helm_values(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate Helm values for vector store deployment"""
        pass
    
    @abstractmethod
    def get_chart_reference(self) -> Dict[str, str]:
        """Get Helm chart repository and version information"""
        pass
    
    @abstractmethod
    def get_default_configuration(self, cluster_size: ClusterSize) -> VectorStoreConfiguration:
        """Get default configuration based on cluster size"""
        pass


class WeaviateProvider(VectorStoreProvider):
    """Weaviate vector database provider implementation"""
    
    def generate_helm_values(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate Weaviate-specific Helm values"""
        base_config = self.get_default_configuration(cluster_config.size)
        
        values = {
            "replicas": base_config.replicas,
            "resources": {
                "requests": {
                    "memory": base_config.memory_allocation,
                    "cpu": base_config.cpu_allocation
                },
                "limits": {
                    "memory": base_config.memory_allocation,
                    "cpu": base_config.cpu_allocation
                }
            },
            "persistence": {
                "enabled": True,
                "size": base_config.storage_size,
                "storageClassName": "openebs-hostpath"
            },
            "authentication": {
                "enabled": base_config.authentication_enabled,
                "anonymous_access_enabled": False
            },
            "authorization": {
                "enabled": True,
                "admin_list": [
                    "admin@vectorweight.com",
                    "ai-team@vectorweight.com"
                ]
            },
            "modules": {
                "text2vec-transformers": {"enabled": True},
                "text2vec-openai": {"enabled": True},
                "generative-openai": {"enabled": True},
                "qna-transformers": {"enabled": True},
                "ref2vec-centroid": {"enabled": True}
            },
            "queryDefaults": {
                "limit": 100
            },
            "monitoring": {
                "enabled": base_config.monitoring_enabled,
                "serviceMonitor": {
                    "enabled": True,
                    "namespace": "monitoring"
                }
            },
            "backup": {
                "enabled": base_config.backup_enabled,
                "schedule": "0 2 * * *",
                "retention": "30d"
            }
        }
        
        # Apply cluster-specific optimizations
        if cluster_config.size == ClusterSize.MINIMAL:
            values["modules"] = {
                "text2vec-transformers": {"enabled": True}
            }
            values["backup"]["enabled"] = False
        
        return values
    
    def get_chart_reference(self) -> Dict[str, str]:
        """Get Weaviate Helm chart information"""
        return {
            "repository": "https://weaviate.github.io/weaviate-helm",
            "chart": "weaviate",
            "version": "25.2.3"
        }
    
    def get_default_configuration(self, cluster_size: ClusterSize) -> VectorStoreConfiguration:
        """Get Weaviate default configuration based on cluster size"""
        size_configurations = {
            ClusterSize.MINIMAL: VectorStoreConfiguration(
                provider="weaviate",
                namespace="vector-stores",
                storage_size="50Gi",
                memory_allocation="4Gi",
                cpu_allocation="1",
                replicas=1,
                authentication_enabled=True,
                encryption_enabled=True,
                monitoring_enabled=False,
                backup_enabled=False
            ),
            ClusterSize.SMALL: VectorStoreConfiguration(
                provider="weaviate",
                namespace="vector-stores",
                storage_size="100Gi",
                memory_allocation="8Gi",
                cpu_allocation="2",
                replicas=2,
                authentication_enabled=True,
                encryption_enabled=True,
                monitoring_enabled=True,
                backup_enabled=True
            ),
            ClusterSize.MEDIUM: VectorStoreConfiguration(
                provider="weaviate",
                namespace="vector-stores",
                storage_size="250Gi",
                memory_allocation="16Gi",
                cpu_allocation="4",
                replicas=3,
                authentication_enabled=True,
                encryption_enabled=True,
                monitoring_enabled=True,
                backup_enabled=True
            ),
            ClusterSize.LARGE: VectorStoreConfiguration(
                provider="weaviate",
                namespace="vector-stores",
                storage_size="500Gi",
                memory_allocation="32Gi",
                cpu_allocation="8",
                replicas=5,
                authentication_enabled=True,
                encryption_enabled=True,
                monitoring_enabled=True,
                backup_enabled=True
            )
        }
        
        return size_configurations.get(cluster_size, size_configurations[ClusterSize.SMALL])


class QdrantProvider(VectorStoreProvider):
    """Qdrant vector database provider implementation"""
    
    def generate_helm_values(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate Qdrant-specific Helm values"""
        base_config = self.get_default_configuration(cluster_config.size)
        
        values = {
            "replicaCount": base_config.replicas,
            "image": {
                "repository": "qdrant/qdrant",
                "tag": "v1.7.0"
            },
            "resources": {
                "requests": {
                    "memory": base_config.memory_allocation,
                    "cpu": base_config.cpu_allocation
                },
                "limits": {
                    "memory": base_config.memory_allocation,
                    "cpu": base_config.cpu_allocation
                }
            },
            "persistence": {
                "enabled": True,
                "size": base_config.storage_size,
                "storageClass": "openebs-hostpath"
            },
            "config": {
                "cluster": {
                    "enabled": base_config.replicas > 1,
                    "p2p": {
                        "port": 6335
                    }
                },
                "storage": {
                    "performance": {
                        "max_search_threads": 4
                    }
                }
            },
            "service": {
                "type": "ClusterIP",
                "port": 6333,
                "grpcPort": 6334
            },
            "monitoring": {
                "enabled": base_config.monitoring_enabled,
                "serviceMonitor": {
                    "enabled": True,
                    "namespace": "monitoring"
                }
            }
        }
        
        # Apply security configurations
        if base_config.authentication_enabled:
            values["config"]["service"] = {
                "api_key": "${QDRANT_API_KEY}"
            }
        
        return values
    
    def get_chart_reference(self) -> Dict[str, str]:
        """Get Qdrant Helm chart information"""
        return {
            "repository": "https://qdrant.github.io/qdrant-helm",
            "chart": "qdrant",
            "version": "0.7.0"
        }
    
    def get_default_configuration(self, cluster_size: ClusterSize) -> VectorStoreConfiguration:
        """Get Qdrant default configuration based on cluster size"""
        size_configurations = {
            ClusterSize.MINIMAL: VectorStoreConfiguration(
                provider="qdrant",
                namespace="vector-stores",
                storage_size="20Gi",
                memory_allocation="2Gi",
                cpu_allocation="500m",
                replicas=1,
                authentication_enabled=True,
                encryption_enabled=True,
                monitoring_enabled=False,
                backup_enabled=False
            ),
            ClusterSize.SMALL: VectorStoreConfiguration(
                provider="qdrant",
                namespace="vector-stores",
                storage_size="50Gi",
                memory_allocation="4Gi",
                cpu_allocation="1",
                replicas=2,
                authentication_enabled=True,
                encryption_enabled=True,
                monitoring_enabled=True,
                backup_enabled=True
            ),
            ClusterSize.MEDIUM: VectorStoreConfiguration(
                provider="qdrant",
                namespace="vector-stores",
                storage_size="100Gi",
                memory_allocation="8Gi",
                cpu_allocation="2",
                replicas=3,
                authentication_enabled=True,
                encryption_enabled=True,
                monitoring_enabled=True,
                backup_enabled=True
            ),
            ClusterSize.LARGE: VectorStoreConfiguration(
                provider="qdrant",
                namespace="vector-stores",
                storage_size="200Gi",
                memory_allocation="16Gi",
                cpu_allocation="4",
                replicas=5,
                authentication_enabled=True,
                encryption_enabled=True,
                monitoring_enabled=True,
                backup_enabled=True
            )
        }
        
        return size_configurations.get(cluster_size, size_configurations[ClusterSize.SMALL])


class ChromaProvider(VectorStoreProvider):
    """Chroma vector database provider implementation"""
    
    def generate_helm_values(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate Chroma-specific Helm values"""
        base_config = self.get_default_configuration(cluster_config.size)
        
        values = {
            "replicaCount": base_config.replicas,
            "image": {
                "repository": "chromadb/chroma",
                "tag": "0.4.15"
            },
            "resources": {
                "requests": {
                    "memory": base_config.memory_allocation,
                    "cpu": base_config.cpu_allocation
                },
                "limits": {
                    "memory": base_config.memory_allocation,
                    "cpu": base_config.cpu_allocation
                }
            },
            "persistence": {
                "enabled": True,
                "size": base_config.storage_size,
                "storageClass": "openebs-hostpath"
            },
            "config": {
                "chroma_server_auth_provider": "chromadb.auth.basic.BasicAuthServerProvider" if base_config.authentication_enabled else None,
                "chroma_server_auth_credentials_file": "/etc/chroma/credentials" if base_config.authentication_enabled else None
            },
            "service": {
                "type": "ClusterIP",
                "port": 8000
            }
        }
        
        # Remove None values from config
        values["config"] = {k: v for k, v in values["config"].items() if v is not None}
        
        return values
    
    def get_chart_reference(self) -> Dict[str, str]:
        """Get Chroma Helm chart information"""
        return {
            "repository": "https://amikos-tech.github.io/chromadb-chart/",
            "chart": "chromadb",
            "version": "0.1.0"
        }
    
    def get_default_configuration(self, cluster_size: ClusterSize) -> VectorStoreConfiguration:
        """Get Chroma default configuration based on cluster size"""
        size_configurations = {
            ClusterSize.MINIMAL: VectorStoreConfiguration(
                provider="chroma",
                namespace="vector-stores",
                storage_size="10Gi",
                memory_allocation="1Gi",
                cpu_allocation="250m",
                replicas=1,
                authentication_enabled=True,
                encryption_enabled=False,
                monitoring_enabled=False,
                backup_enabled=False
            ),
            ClusterSize.SMALL: VectorStoreConfiguration(
                provider="chroma",
                namespace="vector-stores",
                storage_size="25Gi",
                memory_allocation="2Gi",
                cpu_allocation="500m",
                replicas=2,
                authentication_enabled=True,
                encryption_enabled=False,
                monitoring_enabled=True,
                backup_enabled=True
            ),
            ClusterSize.MEDIUM: VectorStoreConfiguration(
                provider="chroma",
                namespace="vector-stores",
                storage_size="50Gi",
                memory_allocation="4Gi",
                cpu_allocation="1",
                replicas=3,
                authentication_enabled=True,
                encryption_enabled=False,
                monitoring_enabled=True,
                backup_enabled=True
            ),
            ClusterSize.LARGE: VectorStoreConfiguration(
                provider="chroma",
                namespace="vector-stores",
                storage_size="100Gi",
                memory_allocation="8Gi",
                cpu_allocation="2",
                replicas=5,
                authentication_enabled=True,
                encryption_enabled=False,
                monitoring_enabled=True,
                backup_enabled=True
            )
        }
        
        return size_configurations.get(cluster_size, size_configurations[ClusterSize.SMALL])


class ChromaInMemoryProvider(VectorStoreProvider):
    """In-memory Chroma provider for rapid prototyping"""
    
    def generate_helm_values(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate in-memory Chroma configuration"""
        return {
            "replicaCount": 1,
            "image": {
                "repository": "chromadb/chroma",
                "tag": "0.4.15"
            },
            "resources": {
                "requests": {
                    "memory": "512Mi",
                    "cpu": "100m"
                },
                "limits": {
                    "memory": "1Gi",
                    "cpu": "250m"
                }
            },
            "persistence": {
                "enabled": False
            },
            "config": {
                "is_persistent": False,
                "chroma_memory_limit_bytes": 536870912  # 512MB
            },
            "service": {
                "type": "ClusterIP",
                "port": 8000
            }
        }
    
    def get_chart_reference(self) -> Dict[str, str]:
        """Get Chroma chart information"""
        return {
            "repository": "https://amikos-tech.github.io/chromadb-chart/",
            "chart": "chromadb",
            "version": "0.1.0"
        }
    
    def get_default_configuration(self, cluster_size: ClusterSize) -> VectorStoreConfiguration:
        """Get in-memory Chroma configuration"""
        return VectorStoreConfiguration(
            provider="chroma-memory",
            namespace="vector-stores",
            storage_size="0Gi",
            memory_allocation="1Gi",
            cpu_allocation="250m",
            replicas=1,
            authentication_enabled=False,
            encryption_enabled=False,
            monitoring_enabled=False,
            backup_enabled=False
        )


class VectorStoreIntegrationManager:
    """Central manager for vector store integrations"""
    
    def __init__(self):
        self.providers = {
            VectorStoreType.WEAVIATE: WeaviateProvider(),
            VectorStoreType.QDRANT: QdrantProvider(),
            VectorStoreType.CHROMA: ChromaProvider(),
            VectorStoreType.CHROMA_MEMORY: ChromaInMemoryProvider()
        }
    
    def get_provider(self, vector_store_type: VectorStoreType) -> VectorStoreProvider:
        """Get provider instance for vector store type"""
        if vector_store_type not in self.providers:
            raise ValueError(f"Unsupported vector store type: {vector_store_type}")
        
        return self.providers[vector_store_type]
    
    def generate_configuration(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate complete vector store configuration"""
        if cluster_config.vector_store == VectorStoreType.DISABLED:
            return {}
        
        provider = self.get_provider(cluster_config.vector_store)
        
        configuration = {
            "enabled": True,
            "provider": cluster_config.vector_store.value,
            "chart": provider.get_chart_reference(),
            "values": provider.generate_helm_values(cluster_config),
            "namespace": "vector-stores"
        }
        
        # Add security configurations
        configuration["security"] = self._generate_security_configuration(cluster_config)
        
        # Add networking configurations
        configuration["networking"] = self._generate_networking_configuration(cluster_config)
        
        logger.info(f"Generated {cluster_config.vector_store.value} configuration for {cluster_config.name}")
        
        return configuration
    
    def _generate_security_configuration(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate security configuration for vector store"""
        return {
            "networkPolicy": {
                "enabled": True,
                "ingress": [
                    {
                        "from": [
                            {"namespaceSelector": {"matchLabels": {"name": "ai-workloads"}}},
                            {"namespaceSelector": {"matchLabels": {"name": "applications"}}}
                        ],
                        "ports": [
                            {"protocol": "TCP", "port": 8000},  # HTTP API
                            {"protocol": "TCP", "port": 6333},  # Qdrant
                            {"protocol": "TCP", "port": 6334}   # Qdrant gRPC
                        ]
                    }
                ],
                "egress": [
                    {
                        "to": [
                            {"namespaceSelector": {"matchLabels": {"name": "authorization"}}}
                        ],
                        "ports": [
                            {"protocol": "TCP", "port": 3593}  # Cerbos
                        ]
                    }
                ]
            },
            "podSecurityPolicy": {
                "enabled": True,
                "runAsNonRoot": True,
                "runAsUser": 65534,
                "runAsGroup": 65534,
                "fsGroup": 65534,
                "seccompProfile": {
                    "type": "RuntimeDefault"
                }
            }
        }
    
    def _generate_networking_configuration(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate networking configuration for vector store"""
        return {
            "service": {
                "type": "ClusterIP",
                "annotations": {
                    "service.beta.kubernetes.io/aws-load-balancer-internal": "true"
                }
            },
            "ingress": {
                "enabled": True,
                "className": "istio",
                "annotations": {
                    "cert-manager.io/cluster-issuer": "letsencrypt-prod",
                    "kubernetes.io/tls-acme": "true"
                },
                "hosts": [
                    {
                        "host": f"vector-store.{cluster_config.domain}",
                        "paths": [
                            {
                                "path": "/",
                                "pathType": "Prefix"
                            }
                        ]
                    }
                ],
                "tls": [
                    {
                        "secretName": f"vector-store-{cluster_config.name}-tls",
                        "hosts": [f"vector-store.{cluster_config.domain}"]
                    }
                ]
            }
        }
    
    @staticmethod
    def generate_weaviate_configuration(cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Static method for backward compatibility"""
        manager = VectorStoreIntegrationManager()
        return manager.generate_configuration(cluster_config)
    
    @staticmethod
    def generate_qdrant_configuration(cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Static method for backward compatibility"""
        manager = VectorStoreIntegrationManager()
        cluster_config.vector_store = VectorStoreType.QDRANT
        return manager.generate_configuration(cluster_config)
    
    def list_supported_providers(self) -> List[str]:
        """List all supported vector store providers"""
        return [provider.value for provider in self.providers.keys()]
    
    def validate_configuration(self, cluster_config: ClusterConfiguration) -> List[str]:
        """Validate vector store configuration and return warnings/errors"""
        warnings = []
        
        if cluster_config.vector_store == VectorStoreType.DISABLED:
            return warnings
        
        # Check cluster size compatibility
        if cluster_config.vector_store == VectorStoreType.WEAVIATE and cluster_config.size == ClusterSize.MINIMAL:
            warnings.append("Weaviate may require more resources than available in minimal cluster size")
        
        # Check GPU requirements
        if cluster_config.vector_store in [VectorStoreType.WEAVIATE] and not cluster_config.gpu_enabled:
            warnings.append("Consider enabling GPU support for optimal vector processing performance")
        
        # Check memory requirements for in-memory providers
        if cluster_config.vector_store == VectorStoreType.CHROMA_MEMORY:
            warnings.append("In-memory vector store will lose data on pod restarts")
        
        return warnings
