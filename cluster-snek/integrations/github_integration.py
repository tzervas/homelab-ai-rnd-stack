#!/usr/bin/env python3
"""
GitHub API Integration Module
Professional GitHub repository management using PyGithub
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from github import Github, GithubException, Repository
from github.ContentFile import ContentFile

logger = logging.getLogger(__name__)


@dataclass
class RepositoryTemplate:
    """Template configuration for repository creation"""
    name: str
    description: str
    private: bool = False
    has_issues: bool = True
    has_wiki: bool = False
    has_downloads: bool = False
    default_branch: str = "main"
    gitignore_template: Optional[str] = "Python"
    license_template: Optional[str] = None


class GitHubRepositoryManager:
    """Manages GitHub repository operations using PyGithub API"""
    
    def __init__(self, token: str, organization: str):
        """
        Initialize GitHub API client
        
        Args:
            token: GitHub personal access token with repo permissions
            organization: Target GitHub organization name
        """
        self.github = Github(token)
        self.organization_name = organization
        self._organization = None
        self._user = None
        
        # Validate authentication and permissions
        self._validate_authentication()
    
    def _validate_authentication(self) -> None:
        """Validate GitHub authentication and organization access"""
        try:
            self._user = self.github.get_user()
            logger.info(f"Authenticated as GitHub user: {self._user.login}")
            
            # Verify organization access
            try:
                self._organization = self.github.get_organization(self.organization_name)
                logger.info(f"Organization access confirmed: {self.organization_name}")
            except GithubException as e:
                if e.status == 404:
                    logger.warning(f"Organization {self.organization_name} not found or no access")
                    # Fall back to user repositories
                    self._organization = None
                else:
                    raise
                    
        except GithubException as e:
            logger.error(f"GitHub authentication failed: {e}")
            raise ValueError(f"Invalid GitHub token or insufficient permissions: {e}")
    
    def repository_exists(self, repository_name: str) -> bool:
        """
        Check if repository exists in organization or user account
        
        Args:
            repository_name: Name of repository to check
            
        Returns:
            True if repository exists, False otherwise
        """
        try:
            self._get_repository(repository_name)
            return True
        except GithubException as e:
            if e.status == 404:
                return False
            raise
    
    def _get_repository(self, repository_name: str) -> Repository:
        """Get repository object from GitHub API"""
        if self._organization:
            return self._organization.get_repo(repository_name)
        else:
            return self._user.get_repo(repository_name)
    
    def create_repository(self, template: RepositoryTemplate) -> Repository:
        """
        Create new GitHub repository with specified configuration
        
        Args:
            template: Repository configuration template
            
        Returns:
            Created repository object
            
        Raises:
            ValueError: If repository already exists
            GithubException: If creation fails
        """
        if self.repository_exists(template.name):
            logger.warning(f"Repository {template.name} already exists")
            return self._get_repository(template.name)
        
        try:
            if self._organization:
                repo = self._organization.create_repo(
                    name=template.name,
                    description=template.description,
                    private=template.private,
                    has_issues=template.has_issues,
                    has_wiki=template.has_wiki,
                    has_downloads=template.has_downloads,
                    gitignore_template=template.gitignore_template,
                    license_template=template.license_template
                )
            else:
                repo = self._user.create_repo(
                    name=template.name,
                    description=template.description,
                    private=template.private,
                    has_issues=template.has_issues,
                    has_wiki=template.has_wiki,
                    has_downloads=template.has_downloads,
                    gitignore_template=template.gitignore_template,
                    license_template=template.license_template
                )
            
            logger.info(f"Created repository: {repo.full_name}")
            return repo
            
        except GithubException as e:
            logger.error(f"Repository creation failed: {e}")
            raise
    
    def update_repository_content(self, repository_name: str, content_map: Dict[str, str]) -> None:
        """
        Update repository content with file mappings
        
        Args:
            repository_name: Target repository name
            content_map: Dictionary mapping file paths to content
        """
        repo = self._get_repository(repository_name)
        
        for file_path, content in content_map.items():
            try:
                # Check if file exists
                try:
                    existing_file = repo.get_contents(file_path)
                    # Update existing file
                    repo.update_file(
                        path=file_path,
                        message=f"Update {file_path}",
                        content=content,
                        sha=existing_file.sha
                    )
                    logger.debug(f"Updated file: {file_path}")
                    
                except GithubException as e:
                    if e.status == 404:
                        # Create new file
                        repo.create_file(
                            path=file_path,
                            message=f"Add {file_path}",
                            content=content
                        )
                        logger.debug(f"Created file: {file_path}")
                    else:
                        raise
                        
            except GithubException as e:
                logger.error(f"Failed to update {file_path}: {e}")
                raise
    
    def setup_branch_protection(self, repository_name: str) -> None:
        """
        Configure branch protection rules for main branch
        
        Args:
            repository_name: Target repository name
        """
        repo = self._get_repository(repository_name)
        
        try:
            main_branch = repo.get_branch("main")
            main_branch.edit_protection(
                strict=True,
                contexts=[],
                enforce_admins=False,
                dismiss_stale_reviews=True,
                require_code_owner_reviews=False,
                required_approving_review_count=1
            )
            logger.info(f"Branch protection configured for {repository_name}")
            
        except GithubException as e:
            logger.warning(f"Branch protection setup failed: {e}")
    
    def create_deployment_key(self, repository_name: str, key_title: str, 
                           public_key: str, read_only: bool = True) -> None:
        """
        Add deployment key to repository
        
        Args:
            repository_name: Target repository name
            key_title: Title for the deployment key
            public_key: SSH public key content
            read_only: Whether key should be read-only
        """
        repo = self._get_repository(repository_name)
        
        try:
            repo.create_key(
                title=key_title,
                key=public_key,
                read_only=read_only
            )
            logger.info(f"Deployment key '{key_title}' added to {repository_name}")
            
        except GithubException as e:
            logger.error(f"Failed to add deployment key: {e}")
            raise
    
    def list_repositories(self) -> List[str]:
        """
        List all accessible repositories
        
        Returns:
            List of repository names
        """
        repositories = []
        
        if self._organization:
            for repo in self._organization.get_repos():
                repositories.append(repo.name)
        else:
            for repo in self._user.get_repos():
                repositories.append(repo.name)
        
        return repositories
    
    def delete_repository(self, repository_name: str) -> None:
        """
        Delete repository (use with caution)
        
        Args:
            repository_name: Repository to delete
        """
        repo = self._get_repository(repository_name)
        
        try:
            repo.delete()
            logger.warning(f"Deleted repository: {repository_name}")
            
        except GithubException as e:
            logger.error(f"Repository deletion failed: {e}")
            raise


class VectorWeightRepositoryOrchestrator:
    """High-level orchestrator for VectorWeight repository management"""
    
    def __init__(self, github_manager: GitHubRepositoryManager):
        self.github = github_manager
        self.cluster_templates = self._initialize_cluster_templates()
        self.orchestration_template = self._initialize_orchestration_template()
    
    def _initialize_cluster_templates(self) -> Dict[str, RepositoryTemplate]:
        """Initialize repository templates for cluster configurations"""
        return {
            "dev-cluster": RepositoryTemplate(
                name="dev-cluster",
                description="VectorWeight development cluster configuration",
                private=False
            ),
            "ai-cluster": RepositoryTemplate(
                name="ai-cluster", 
                description="VectorWeight AI/ML cluster configuration",
                private=False
            ),
            "homelab-cluster": RepositoryTemplate(
                name="homelab-cluster",
                description="VectorWeight homelab cluster configuration", 
                private=False
            ),
            "security-cluster": RepositoryTemplate(
                name="security-cluster",
                description="VectorWeight security and monitoring cluster configuration",
                private=False
            )
        }
    
    def _initialize_orchestration_template(self) -> RepositoryTemplate:
        """Initialize orchestration repository template"""
        return RepositoryTemplate(
            name="orchestration-repo",
            description="VectorWeight central GitOps orchestration repository",
            private=False
        )
    
    def ensure_repositories_exist(self, cluster_names: List[str]) -> Dict[str, Repository]:
        """
        Ensure all required repositories exist, creating if necessary
        
        Args:
            cluster_names: List of cluster names requiring repositories
            
        Returns:
            Dictionary mapping cluster names to repository objects
        """
        repositories = {}
        
        # Create cluster repositories
        for cluster_name in cluster_names:
            template = self.cluster_templates.get(cluster_name)
            if not template:
                template = RepositoryTemplate(
                    name=cluster_name,
                    description=f"VectorWeight {cluster_name} cluster configuration",
                    private=False
                )
            
            repo = self.github.create_repository(template)
            repositories[cluster_name] = repo
            
            # Configure branch protection
            self.github.setup_branch_protection(cluster_name)
        
        # Create orchestration repository
        orchestration_repo = self.github.create_repository(self.orchestration_template)
        repositories["orchestration"] = orchestration_repo
        self.github.setup_branch_protection("orchestration-repo")
        
        return repositories
    
    def populate_repository_content(self, repository_name: str, 
                                  content_generator) -> None:
        """
        Populate repository with generated content
        
        Args:
            repository_name: Target repository name
            content_generator: Generator function that produces content mapping
        """
        content_map = content_generator(repository_name)
        self.github.update_repository_content(repository_name, content_map)
        
        logger.info(f"Repository {repository_name} populated with generated content")
