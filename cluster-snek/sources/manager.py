#!/usr/bin/env python3
"""
Source Management System
Comprehensive source handling for airgapped and connected deployments
"""

import logging
import shutil
import tempfile
import hashlib
import tarfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union, Protocol
from urllib.parse import urlparse
from dataclasses import dataclass

import git
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


@dataclass
class SourceVerification:
    """Source verification configuration"""
    checksum: Optional[str] = None
    checksum_algorithm: str = "sha256"
    signature_file: Optional[Path] = None
    gpg_key_id: Optional[str] = None


@dataclass
class SourceMetadata:
    """Metadata for source content"""
    source_type: str
    source_url: Optional[str]
    local_path: Path
    verification: Optional[SourceVerification] = None
    last_updated: Optional[str] = None


class SourceHandler(Protocol):
    """Protocol defining source handler interface"""
    
    def fetch(self, destination: Path) -> SourceMetadata:
        """Fetch source content to destination directory"""
        ...
    
    def verify(self, metadata: SourceMetadata) -> bool:
        """Verify source content integrity"""
        ...


class GitSourceHandler:
    """Handler for Git repository sources"""
    
    def __init__(self, url: str, username: Optional[str] = None, 
                 token: Optional[str] = None, branch: str = "main"):
        self.url = url
        self.username = username
        self.token = token
        self.branch = branch
    
    def fetch(self, destination: Path) -> SourceMetadata:
        """Clone Git repository to destination"""
        try:
            # Prepare authentication if credentials provided
            env_vars = {}
            if self.username and self.token:
                # Use token authentication for HTTPS URLs
                parsed_url = urlparse(self.url)
                authenticated_url = f"{parsed_url.scheme}://{self.username}:{self.token}@{parsed_url.netloc}{parsed_url.path}"
            else:
                authenticated_url = self.url
            
            # Clone repository
            repo = git.Repo.clone_from(
                authenticated_url,
                destination,
                branch=self.branch,
                depth=1  # Shallow clone for efficiency
            )
            
            # Get commit information for verification
            latest_commit = repo.head.commit
            
            logger.info(f"Cloned repository {self.url} to {destination}")
            
            return SourceMetadata(
                source_type="git",
                source_url=self.url,
                local_path=destination,
                last_updated=latest_commit.committed_datetime.isoformat()
            )
            
        except git.GitCommandError as e:
            logger.error(f"Git clone failed: {e}")
            raise ValueError(f"Failed to clone repository {self.url}: {e}")


class ArchiveSourceHandler:
    """Handler for archive file sources (tar.gz, zip, etc.)"""
    
    def __init__(self, source_path: Union[str, Path], 
                 verification: Optional[SourceVerification] = None):
        self.source_path = Path(source_path) if isinstance(source_path, str) else source_path
        self.verification = verification
    
    def fetch(self, destination: Path) -> SourceMetadata:
        """Extract archive to destination"""
        try:
            if self.source_path.is_file():
                # Local archive file
                archive_path = self.source_path
            else:
                # Remote archive - download first
                archive_path = self._download_archive(destination)
            
            # Verify archive if verification configured
            if self.verification:
                if not self._verify_archive(archive_path):
                    raise ValueError("Archive verification failed")
            
            # Extract archive
            self._extract_archive(archive_path, destination)
            
            logger.info(f"Extracted archive {self.source_path} to {destination}")
            
            return SourceMetadata(
                source_type="archive",
                source_url=str(self.source_path),
                local_path=destination,
                verification=self.verification
            )
            
        except Exception as e:
            logger.error(f"Archive extraction failed: {e}")
            raise
    
    def _download_archive(self, temp_dir: Path) -> Path:
        """Download remote archive file"""
        archive_name = Path(self.source_path).name
        local_archive = temp_dir / f"download_{archive_name}"
        
        response = requests.get(str(self.source_path), stream=True)
        response.raise_for_status()
        
        with open(local_archive, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return local_archive
    
    def _verify_archive(self, archive_path: Path) -> bool:
        """Verify archive integrity using checksum"""
        if not self.verification or not self.verification.checksum:
            return True
        
        hash_algo = getattr(hashlib, self.verification.checksum_algorithm)
        calculated_hash = hash_algo()
        
        with open(archive_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                calculated_hash.update(chunk)
        
        return calculated_hash.hexdigest() == self.verification.checksum
    
    def _extract_archive(self, archive_path: Path, destination: Path) -> None:
        """Extract archive based on file extension"""
        destination.mkdir(parents=True, exist_ok=True)
        
        if archive_path.suffix in ['.tar', '.tar.gz', '.tgz']:
            with tarfile.open(archive_path, 'r:*') as tar:
                tar.extractall(destination)
        elif archive_path.suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_file:
                zip_file.extractall(destination)
        else:
            raise ValueError(f"Unsupported archive format: {archive_path.suffix}")


class LocalSourceHandler:
    """Handler for local filesystem sources"""
    
    def __init__(self, source_path: Path):
        self.source_path = source_path
    
    def fetch(self, destination: Path) -> SourceMetadata:
        """Copy local source to destination"""
        try:
            if not self.source_path.exists():
                raise FileNotFoundError(f"Source path does not exist: {self.source_path}")
            
            destination.mkdir(parents=True, exist_ok=True)
            
            if self.source_path.is_file():
                shutil.copy2(self.source_path, destination)
            else:
                shutil.copytree(self.source_path, destination / self.source_path.name, 
                              dirs_exist_ok=True)
            
            logger.info(f"Copied local source {self.source_path} to {destination}")
            
            return SourceMetadata(
                source_type="local",
                source_url=None,
                local_path=destination
            )
            
        except Exception as e:
            logger.error(f"Local source copy failed: {e}")
            raise


class NetworkSourceHandler:
    """Handler for network-based sources (HTTP, SMB, NFS, etc.)"""
    
    def __init__(self, url: str, username: Optional[str] = None, 
                 password: Optional[str] = None):
        self.url = url
        self.username = username
        self.password = password
    
    def fetch(self, destination: Path) -> SourceMetadata:
        """Fetch from network source"""
        parsed_url = urlparse(self.url)
        
        if parsed_url.scheme in ['http', 'https']:
            return self._fetch_http(destination)
        elif parsed_url.scheme in ['smb', 'cifs']:
            return self._fetch_smb(destination)
        elif parsed_url.scheme == 'nfs':
            return self._fetch_nfs(destination)
        else:
            raise ValueError(f"Unsupported network protocol: {parsed_url.scheme}")
    
    def _fetch_http(self, destination: Path) -> SourceMetadata:
        """Fetch via HTTP/HTTPS"""
        auth = HTTPBasicAuth(self.username, self.password) if self.username else None
        
        response = requests.get(self.url, auth=auth, stream=True)
        response.raise_for_status()
        
        # Determine filename from URL or Content-Disposition header
        filename = self._get_filename_from_response(response)
        file_path = destination / filename
        
        destination.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded {self.url} to {file_path}")
        
        return SourceMetadata(
            source_type="network_http",
            source_url=self.url,
            local_path=destination
        )
    
    def _fetch_smb(self, destination: Path) -> SourceMetadata:
        """Fetch via SMB/CIFS"""
        # Implementation would require smbprotocol or similar library
        # For demonstration purposes, showing interface
        raise NotImplementedError("SMB support requires additional dependencies")
    
    def _fetch_nfs(self, destination: Path) -> SourceMetadata:
        """Fetch via NFS"""
        # Implementation would require NFS client tools
        raise NotImplementedError("NFS support requires system-level configuration")
    
    def _get_filename_from_response(self, response: requests.Response) -> str:
        """Extract filename from HTTP response"""
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            # Parse Content-Disposition header
            import re
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if filename_match:
                return filename_match.group(1)
        
        # Fall back to URL path
        parsed_url = urlparse(response.url)
        return Path(parsed_url.path).name or "downloaded_file"


class SourceManager:
    """Central source management orchestrator"""
    
    def __init__(self, temp_directory: Optional[Path] = None):
        self.temp_directory = temp_directory or Path(tempfile.mkdtemp())
        self.source_cache: Dict[str, SourceMetadata] = {}
    
    def fetch_source(self, source_config: "SourceConfiguration") -> SourceMetadata:
        """
        Fetch source content based on configuration
        
        Args:
            source_config: Source configuration specification
            
        Returns:
            Source metadata with local path information
        """
        # Generate cache key for idempotent operations
        cache_key = self._generate_cache_key(source_config)
        
        # Return cached source if available and valid
        if cache_key in self.source_cache:
            cached_metadata = self.source_cache[cache_key]
            if cached_metadata.local_path.exists():
                logger.info(f"Using cached source: {cached_metadata.local_path}")
                return cached_metadata
        
        # Create destination directory
        destination = self.temp_directory / f"source_{cache_key}"
        destination.mkdir(parents=True, exist_ok=True)
        
        # Select appropriate handler based on source configuration
        handler = self._create_source_handler(source_config)
        
        # Fetch source content
        metadata = handler.fetch(destination)
        
        # Cache metadata for future use
        self.source_cache[cache_key] = metadata
        
        logger.info(f"Source fetched successfully: {metadata.source_type}")
        return metadata
    
    def _create_source_handler(self, source_config: "SourceConfiguration") -> SourceHandler:
        """Create appropriate source handler based on configuration"""
        from .config.schema import DeploymentMode
        
        if source_config.mode == DeploymentMode.AIRGAPPED_VC:
            return GitSourceHandler(
                url=source_config.url,
                username=source_config.username,
                token=source_config.token
            )
        elif source_config.mode == DeploymentMode.AIRGAPPED_LOCAL:
            return LocalSourceHandler(source_config.path)
        elif source_config.mode == DeploymentMode.AIRGAPPED_NETWORK:
            return NetworkSourceHandler(
                url=source_config.url,
                username=source_config.username,
                password=source_config.password
            )
        elif source_config.mode == DeploymentMode.AIRGAPPED_ARCHIVE:
            verification = None
            if source_config.verification_enabled:
                verification = SourceVerification()
            
            if source_config.url:
                return ArchiveSourceHandler(source_config.url, verification)
            else:
                return ArchiveSourceHandler(source_config.path, verification)
        else:
            raise ValueError(f"Unsupported source mode: {source_config.mode}")
    
    def _generate_cache_key(self, source_config: "SourceConfiguration") -> str:
        """Generate unique cache key for source configuration"""
        key_components = [
            source_config.mode.value,
            source_config.url or "",
            str(source_config.path) if source_config.path else "",
            source_config.username or ""
        ]
        
        key_string = "|".join(key_components)
        return hashlib.md5(key_string.encode()).hexdigest()[:8]
    
    def cleanup(self) -> None:
        """Clean up temporary source files"""
        if self.temp_directory.exists():
            shutil.rmtree(self.temp_directory)
            logger.info("Source cache cleaned up")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
