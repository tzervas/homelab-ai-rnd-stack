#!/usr/bin/env python3
"""
Cerbos Authorization Integration Module
Enterprise-grade authorization engine integration for Kubernetes environments
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

from vectorweight.config.schema import ClusterConfiguration, ClusterSize

logger = logging.getLogger(__name__)


@dataclass
class CerbosConfiguration:
    """Cerbos deployment configuration parameters"""
    replicas: int
    namespace: str
    storage_enabled: bool
    storage_size: str
    audit_enabled: bool
    postgres_enabled: bool
    high_availability: bool
    policy_repository: str
    jwt_verification_enabled: bool


@dataclass
class PolicyDefinition:
    """Cerbos policy definition structure"""
    resource_type: str
    actions: List[str]
    conditions: List[str]
    roles: List[str]
    derived_roles: Optional[List[str]] = None


class CerbosIntegrationManager:
    """Central manager for Cerbos authorization engine integration"""
    
    def __init__(self):
        self.default_policies = self._initialize_default_policies()
        self.jwt_issuers = self._initialize_jwt_issuers()
    
    def _initialize_default_policies(self) -> List[PolicyDefinition]:
        """Initialize default policy definitions for VectorWeight deployment"""
        return [
            PolicyDefinition(
                resource_type="vector_stores",
                actions=["read", "write", "query", "index"],
                conditions=[
                    "request.user.department == 'ai-research'",
                    "request.resource.classification <= 'internal'"
                ],
                roles=["data-scientist", "ai-engineer", "researcher"]
            ),
            PolicyDefinition(
                resource_type="ai_models",
                actions=["deploy", "inference", "train", "evaluate"],
                conditions=[
                    "request.user.role in ['ml-engineer', 'ai-architect']",
                    "request.resource.security_scan == 'passed'"
                ],
                roles=["ml-engineer", "ai-architect", "model-deployer"]
            ),
            PolicyDefinition(
                resource_type="kubernetes_resources",
                actions=["create", "read", "update", "delete"],
                conditions=[
                    "request.user.namespace_access contains request.resource.namespace",
                    "request.resource.sensitive != true"
                ],
                roles=["developer", "operator", "admin"],
                derived_roles=["namespace-admin", "cluster-viewer"]
            ),
            PolicyDefinition(
                resource_type="monitoring_data",
                actions=["view", "export", "analyze"],
                conditions=[
                    "request.user.security_clearance >= request.resource.classification",
                    "request.time.hour >= 8 && request.time.hour <= 18"
                ],
                roles=["security-analyst", "site-reliability-engineer", "platform-engineer"]
            )
        ]
    
    def _initialize_jwt_issuers(self) -> List[Dict[str, str]]:
        """Initialize JWT issuer configurations for external identity providers"""
        return [
            {
                "issuer": "https://auth.vectorweight.com",
                "audience": "vectorweight-services",
                "jwks_url": "https://auth.vectorweight.com/.well-known/jwks.json"
            },
            {
                "issuer": "https://keycloak.vectorweight.internal",
                "audience": "kubernetes-api",
                "jwks_url": "https://keycloak.vectorweight.internal/auth/realms/vectorweight/protocol/openid_connect/certs"
            }
        ]
    
    def generate_configuration(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """
        Generate comprehensive Cerbos configuration for cluster deployment
        
        Args:
            cluster_config: Cluster configuration specification
            
        Returns:
            Complete Cerbos deployment configuration dictionary
        """
        base_config = self._get_base_configuration(cluster_config.size)
        
        configuration = {
            "enabled": True,
            "replicas": base_config.replicas,
            "namespace": base_config.namespace,
            "image": {
                "repository": "ghcr.io/cerbos/cerbos",
                "tag": "0.30.0",
                "pullPolicy": "IfNotPresent"
            },
            "resources": self._get_resource_requirements(cluster_config.size),
            "storage": self._generate_storage_configuration(base_config),
            "audit": self._generate_audit_configuration(base_config),
            "postgres": self._generate_postgres_configuration(base_config),
            "policy": self._generate_policy_configuration(base_config),
            "jwt": self._generate_jwt_configuration(),
            "monitoring": self._generate_monitoring_configuration(cluster_config),
            "security": self._generate_security_configuration(),
            "networking": self._generate_networking_configuration(cluster_config)
        }
        
        logger.info(f"Generated Cerbos configuration for cluster: {cluster_config.name}")
        
        return configuration
    
    def _get_base_configuration(self, cluster_size: ClusterSize) -> CerbosConfiguration:
        """Generate base configuration parameters based on cluster size"""
        size_configurations = {
            ClusterSize.MINIMAL: CerbosConfiguration(
                replicas=1,
                namespace="authorization",
                storage_enabled=True,
                storage_size="10Gi",
                audit_enabled=False,
                postgres_enabled=False,
                high_availability=False,
                policy_repository="https://github.com/vectorweight/cerbos-policies",
                jwt_verification_enabled=True
            ),
            ClusterSize.SMALL: CerbosConfiguration(
                replicas=2,
                namespace="authorization",
                storage_enabled=True,
                storage_size="25Gi",
                audit_enabled=True,
                postgres_enabled=True,
                high_availability=True,
                policy_repository="https://github.com/vectorweight/cerbos-policies",
                jwt_verification_enabled=True
            ),
            ClusterSize.MEDIUM: CerbosConfiguration(
                replicas=3,
                namespace="authorization",
                storage_enabled=True,
                storage_size="50Gi",
                audit_enabled=True,
                postgres_enabled=True,
                high_availability=True,
                policy_repository="https://github.com/vectorweight/cerbos-policies",
                jwt_verification_enabled=True
            ),
            ClusterSize.LARGE: CerbosConfiguration(
                replicas=5,
                namespace="authorization",
                storage_enabled=True,
                storage_size="100Gi",
                audit_enabled=True,
                postgres_enabled=True,
                high_availability=True,
                policy_repository="https://github.com/vectorweight/cerbos-policies",
                jwt_verification_enabled=True
            )
        }
        
        return size_configurations.get(cluster_size, size_configurations[ClusterSize.SMALL])
    
    def _get_resource_requirements(self, cluster_size: ClusterSize) -> Dict[str, Any]:
        """Calculate resource requirements based on cluster size"""
        resource_mappings = {
            ClusterSize.MINIMAL: {
                "requests": {"memory": "256Mi", "cpu": "100m"},
                "limits": {"memory": "512Mi", "cpu": "250m"}
            },
            ClusterSize.SMALL: {
                "requests": {"memory": "512Mi", "cpu": "250m"},
                "limits": {"memory": "1Gi", "cpu": "500m"}
            },
            ClusterSize.MEDIUM: {
                "requests": {"memory": "1Gi", "cpu": "500m"},
                "limits": {"memory": "2Gi", "cpu": "1"}
            },
            ClusterSize.LARGE: {
                "requests": {"memory": "2Gi", "cpu": "1"},
                "limits": {"memory": "4Gi", "cpu": "2"}
            }
        }
        
        return resource_mappings.get(cluster_size, resource_mappings[ClusterSize.SMALL])
    
    def _generate_storage_configuration(self, config: CerbosConfiguration) -> Dict[str, Any]:
        """Generate storage configuration for Cerbos deployment"""
        if not config.storage_enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "size": config.storage_size,
            "storageClassName": "openebs-hostpath",
            "accessModes": ["ReadWriteOnce"],
            "annotations": {
                "volume.beta.kubernetes.io/storage-class": "openebs-hostpath"
            }
        }
    
    def _generate_audit_configuration(self, config: CerbosConfiguration) -> Dict[str, Any]:
        """Generate audit logging configuration"""
        if not config.audit_enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "backend": "postgres" if config.postgres_enabled else "file",
            "retention_period": "1y",
            "format": "json",
            "include_metadata": True,
            "exclude_sensitive_data": True,
            "filters": {
                "exclude_health_checks": True,
                "exclude_policy_queries": False,
                "include_decision_logs": True
            }
        }
    
    def _generate_postgres_configuration(self, config: CerbosConfiguration) -> Dict[str, Any]:
        """Generate PostgreSQL backend configuration"""
        if not config.postgres_enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "host": "cerbos-postgres.authorization.svc.cluster.local",
            "port": 5432,
            "database": "cerbos",
            "username": "${CERBOS_DB_USERNAME}",
            "password": "${CERBOS_DB_PASSWORD}",
            "ssl_mode": "require",
            "connection_pool": {
                "max_open_connections": 20,
                "max_idle_connections": 5,
                "connection_max_lifetime": "1h"
            },
            "migration": {
                "auto_migrate": True
            }
        }
    
    def _generate_policy_configuration(self, config: CerbosConfiguration) -> Dict[str, Any]:
        """Generate policy repository and compilation configuration"""
        return {
            "repository": {
                "type": "git",
                "url": config.policy_repository,
                "branch": "main",
                "update_interval": "30s",
                "credentials": {
                    "username": "${CERBOS_POLICY_REPO_USERNAME}",
                    "token": "${CERBOS_POLICY_REPO_TOKEN}"
                }
            },
            "compilation": {
                "fqn_enabled": True,
                "schema_enforcement": "reject",
                "optimization_level": "aggressive",
                "cache_size": "100MB"
            },
            "validation": {
                "enabled": True,
                "strict_mode": True
            },
            "default_policies": self._generate_default_policy_files()
        }
    
    def _generate_default_policy_files(self) -> Dict[str, str]:
        """Generate default policy files for VectorWeight deployment"""
        policy_files = {}
        
        for policy in self.default_policies:
            policy_content = {
                "apiVersion": "api.cerbos.dev/v1",
                "resourcePolicy": {
                    "version": "default",
                    "resource": policy.resource_type,
                    "rules": []
                }
            }
            
            # Generate rules for each action
            for action in policy.actions:
                rule = {
                    "actions": [action],
                    "effect": "EFFECT_ALLOW",
                    "roles": policy.roles,
                    "condition": {
                        "match": {
                            "all": {
                                "of": [
                                    {"expr": condition} for condition in policy.conditions
                                ]
                            }
                        }
                    }
                }
                
                if policy.derived_roles:
                    rule["derivedRoles"] = policy.derived_roles
                
                policy_content["resourcePolicy"]["rules"].append(rule)
            
            # Convert to YAML string representation
            import yaml
            policy_files[f"{policy.resource_type}_policy.yaml"] = yaml.dump(
                policy_content, default_flow_style=False
            )
        
        return policy_files
    
    def _generate_jwt_configuration(self) -> Dict[str, Any]:
        """Generate JWT verification configuration"""
        return {
            "verification": {
                "enabled": True,
                "issuers": self.jwt_issuers,
                "cache": {
                    "enabled": True,
                    "ttl": "1h",
                    "max_entries": 1000
                },
                "key_refresh_interval": "5m"
            },
            "claims_mapping": {
                "user_id": "sub",
                "username": "preferred_username",
                "email": "email",
                "roles": "realm_access.roles",
                "groups": "groups",
                "department": "department",
                "security_clearance": "security_clearance"
            }
        }
    
    def _generate_monitoring_configuration(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate monitoring and observability configuration"""
        return {
            "metrics": {
                "enabled": True,
                "port": 8080,
                "path": "/metrics",
                "service_monitor": {
                    "enabled": True,
                    "namespace": "monitoring",
                    "labels": {
                        "app.kubernetes.io/name": "cerbos",
                        "app.kubernetes.io/instance": f"cerbos-{cluster_config.name}"
                    }
                }
            },
            "tracing": {
                "enabled": True,
                "exporter": "jaeger",
                "endpoint": "jaeger-collector.monitoring.svc.cluster.local:14268",
                "sample_ratio": 0.1
            },
            "health_checks": {
                "enabled": True,
                "liveness_probe": {
                    "path": "/healthz",
                    "port": 8080,
                    "initial_delay_seconds": 30,
                    "period_seconds": 10
                },
                "readiness_probe": {
                    "path": "/readyz",
                    "port": 8080,
                    "initial_delay_seconds": 5,
                    "period_seconds": 5
                }
            }
        }
    
    def _generate_security_configuration(self) -> Dict[str, Any]:
        """Generate security configuration for Cerbos deployment"""
        return {
            "pod_security_context": {
                "run_as_non_root": True,
                "run_as_user": 65534,
                "run_as_group": 65534,
                "fs_group": 65534,
                "seccomp_profile": {
                    "type": "RuntimeDefault"
                }
            },
            "container_security_context": {
                "allow_privilege_escalation": False,
                "read_only_root_filesystem": True,
                "capabilities": {
                    "drop": ["ALL"]
                }
            },
            "network_policy": {
                "enabled": True,
                "ingress": [
                    {
                        "from": [
                            {"namespaceSelector": {"matchLabels": {"name": "vector-stores"}}},
                            {"namespaceSelector": {"matchLabels": {"name": "ai-workloads"}}},
                            {"namespaceSelector": {"matchLabels": {"name": "applications"}}},
                            {"namespaceSelector": {"matchLabels": {"name": "istio-system"}}}
                        ],
                        "ports": [
                            {"protocol": "TCP", "port": 3593},  # Cerbos gRPC
                            {"protocol": "TCP", "port": 3592}   # Cerbos HTTP
                        ]
                    }
                ],
                "egress": [
                    {
                        "to": [
                            {"namespaceSelector": {"matchLabels": {"name": "authorization"}}}
                        ],
                        "ports": [
                            {"protocol": "TCP", "port": 5432}  # PostgreSQL
                        ]
                    },
                    {
                        "to": [],
                        "ports": [
                            {"protocol": "TCP", "port": 443},  # HTTPS for JWT verification
                            {"protocol": "TCP", "port": 53},   # DNS
                            {"protocol": "UDP", "port": 53}    # DNS
                        ]
                    }
                ]
            }
        }
    
    def _generate_networking_configuration(self, cluster_config: ClusterConfiguration) -> Dict[str, Any]:
        """Generate networking configuration for Cerbos service exposure"""
        return {
            "service": {
                "type": "ClusterIP",
                "ports": [
                    {
                        "name": "grpc",
                        "port": 3593,
                        "targetPort": 3593,
                        "protocol": "TCP"
                    },
                    {
                        "name": "http",
                        "port": 3592,
                        "targetPort": 3592,
                        "protocol": "TCP"
                    },
                    {
                        "name": "metrics",
                        "port": 8080,
                        "targetPort": 8080,
                        "protocol": "TCP"
                    }
                ],
                "annotations": {
                    "service.beta.kubernetes.io/aws-load-balancer-internal": "true"
                }
            },
            "ingress": {
                "enabled": False,  # Internal service, no external access
                "className": "istio",
                "annotations": {
                    "cert-manager.io/cluster-issuer": "letsencrypt-prod"
                }
            },
            "virtual_service": {
                "enabled": True,
                "hosts": [f"cerbos.{cluster_config.domain}"],
                "gateways": ["istio-system/default-gateway"],
                "http": [
                    {
                        "match": [{"uri": {"prefix": "/api/cerbos"}}],
                        "route": [
                            {
                                "destination": {
                                    "host": "cerbos.authorization.svc.cluster.local",
                                    "port": {"number": 3592}
                                }
                            }
                        ]
                    }
                ]
            }
        }
    
    @staticmethod
    def generate_chart_reference() -> Dict[str, str]:
        """Get Cerbos Helm chart repository and version information"""
        return {
            "repository": "https://cerbos.dev/helm-charts",
            "chart": "cerbos",
            "version": "0.30.0"
        }
    
    def validate_configuration(self, cluster_config: ClusterConfiguration) -> List[str]:
        """
        Validate Cerbos configuration and return warnings or recommendations
        
        Args:
            cluster_config: Cluster configuration to validate
            
        Returns:
            List of validation warnings or recommendations
        """
        warnings = []
        
        if not cluster_config.cerbos_enabled:
            warnings.append("Cerbos authorization is disabled; consider enabling for enhanced security")
            return warnings
        
        # Check cluster size recommendations
        if cluster_config.size == ClusterSize.MINIMAL:
            warnings.append("Minimal cluster size may impact Cerbos performance in production workloads")
        
        # Check JWT configuration requirements
        if not self.jwt_issuers:
            warnings.append("No JWT issuers configured; external authentication integration will be limited")
        
        # Check policy repository accessibility
        if "github.com" in self.default_policies[0].__dict__.get("policy_repository", ""):
            warnings.append("Ensure policy repository is accessible from cluster network")
        
        # Check resource allocation
        resource_reqs = self._get_resource_requirements(cluster_config.size)
        memory_limit = resource_reqs["limits"]["memory"]
        if memory_limit in ["256Mi", "512Mi"]:
            warnings.append("Consider increasing memory allocation for production Cerbos deployments")
        
        return warnings
    
    def generate_policy_examples(self) -> Dict[str, str]:
        """Generate example policy files for documentation purposes"""
        examples = {}
        
        # Vector store access policy example
        vector_policy = """
apiVersion: api.cerbos.dev/v1
resourcePolicy:
  version: "default"
  resource: "vector_store"
  rules:
    - actions: ["read", "query"]
      effect: EFFECT_ALLOW
      roles: ["data-scientist", "ai-researcher"]
      condition:
        match:
          all:
            of:
              - expr: "request.user.department == 'ai-research'"
              - expr: "request.resource.classification <= 'internal'"
    
    - actions: ["write", "index", "delete"]
      effect: EFFECT_ALLOW
      roles: ["ai-engineer", "data-engineer"]
      condition:
        match:
          all:
            of:
              - expr: "request.user.role in ['ai-engineer', 'data-engineer']"
              - expr: "request.resource.owner == request.user.id || request.user.permissions contains 'admin'"
"""
        
        examples["vector_store_policy_example.yaml"] = vector_policy
        
        # AI model deployment policy example
        model_policy = """
apiVersion: api.cerbos.dev/v1
resourcePolicy:
  version: "default"
  resource: "ai_model"
  rules:
    - actions: ["deploy", "update"]
      effect: EFFECT_ALLOW
      roles: ["ml-engineer", "ai-architect"]
      condition:
        match:
          all:
            of:
              - expr: "request.resource.security_scan == 'passed'"
              - expr: "request.resource.performance_benchmark >= 0.8"
              - expr: "request.user.certification contains 'ml-deployment'"
    
    - actions: ["inference", "evaluate"]
      effect: EFFECT_ALLOW
      roles: ["developer", "data-scientist", "application-user"]
      condition:
        match:
          all:
            of:
              - expr: "request.resource.status == 'production'"
              - expr: "request.user.project_access contains request.resource.project"
"""
        
        examples["ai_model_policy_example.yaml"] = model_policy
        
        return examples
