#!/usr/bin/env python3
"""
VectorWeight CLI Interface
Command-line interface for VectorWeight Homelab deployment automation
"""

import logging
import click
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import json

from vectorweight.config.schema import (
    VectorWaveConfiguration, EXAMPLE_CONFIGURATIONS
)
from vectorweight.config.loader import ConfigurationLoader, ConfigurationValidator
from vectorweight.generators.enhanced import EnhancedVectorWeightGenerator
from vectorweight.utils.logging import setup_logging
from vectorweight.utils.exceptions import ConfigurationError, ValidationError

# Configure logging
logger = logging.getLogger(__name__)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config-file', '-c', type=click.Path(exists=True), 
              help='Configuration file path')
@click.pass_context
def cli(ctx, verbose: bool, config_file: Optional[str]):
    """VectorWeight Homelab - Kubernetes GitOps Deployment Automation"""
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(log_level)
    
    # Initialize context
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config_file
    
    logger.info("VectorWeight Homelab CLI initialized")


@cli.command()
@click.option('--output', '-o', type=click.Path(), default='./vectorweight-config.yaml',
              help='Output configuration file path')
@click.option('--template', '-t', 
              type=click.Choice(['minimal_dev', 'production_full', 'airgapped_enterprise']),
              default='minimal_dev', help='Configuration template to use')
@click.option('--interactive', '-i', is_flag=True, help='Interactive configuration wizard')
def init(output: str, template: str, interactive: bool):
    """Initialize a new VectorWeight configuration"""
    
    output_path = Path(output)
    
    if output_path.exists():
        click.confirm(f"Configuration file {output_path} already exists. Overwrite?", abort=True)
    
    try:
        if interactive:
            config = _interactive_configuration_wizard()
        else:
            # Use predefined template
            config_data = EXAMPLE_CONFIGURATIONS[template]
            loader = ConfigurationLoader()
            config = loader.load_from_dict(config_data)
        
        # Save configuration
        loader = ConfigurationLoader()
        loader.save_to_file(config, output_path)
        
        click.echo(f"✅ Configuration initialized: {output_path}")
        click.echo(f"📝 Template used: {template}")
        click.echo(f"🔧 Edit the configuration file and run 'vectorweight generate' to deploy")
        
    except Exception as e:
        logger.error(f"Configuration initialization failed: {e}")
        click.echo(f"❌ Failed to initialize configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Configuration file path')
@click.option('--output', '-o', type=click.Path(), default='./vectorweight-deployment',
              help='Output directory for generated deployment')
@click.option('--dry-run', is_flag=True, help='Validate configuration without generating')
@click.option('--force', is_flag=True, help='Force regeneration even if no changes detected')
@click.pass_context
def generate(ctx, config: Optional[str], output: str, dry_run: bool, force: bool):
    """Generate VectorWeight homelab deployment"""
    
    config_file = config or ctx.obj.get('config_file')
    
    if not config_file:
        click.echo("❌ No configuration file specified. Use --config or init command first.", err=True)
        sys.exit(1)
    
    try:
        # Load configuration
        loader = ConfigurationLoader()
        configuration = loader.load_from_file(Path(config_file))
        
        click.echo(f"📋 Loaded configuration: {configuration.project_name}")
        click.echo(f"🌍 Environment: {configuration.environment}")
        click.echo(f"🔧 Deployment mode: {configuration.deployment_mode.value}")
        click.echo(f"📦 Clusters: {len(configuration.clusters)}")
        
        # Validate configuration
        validator = ConfigurationValidator()
        validation_messages = validator.validate(configuration)
        
        if validation_messages:
            click.echo("\n📊 Validation Results:")
            for message in validation_messages:
                if message.startswith("Error:"):
                    click.echo(f"❌ {message}", err=True)
                elif message.startswith("Warning:"):
                    click.echo(f"⚠️  {message}")
                else:
                    click.echo(f"ℹ️  {message}")
        
        # Check for errors
        errors = [msg for msg in validation_messages if msg.startswith("Error:")]
        if errors:
            click.echo(f"\n❌ Configuration validation failed with {len(errors)} error(s)")
            sys.exit(1)
        
        if dry_run:
            click.echo("\n✅ Configuration validation completed (dry run)")
            return
        
        # Generate deployment
        click.echo("\n🚀 Generating VectorWeight deployment...")
        
        generator = EnhancedVectorWeightGenerator(configuration)
        generator.output_path = Path(output)
        
        if force:
            generator.state_manager.state["configuration_hash"] = None
        
        generator.generate_complete_deployment()
        
        click.echo(f"\n✅ Deployment generated successfully!")
        click.echo(f"📂 Output directory: {Path(output).absolute()}")
        click.echo(f"🚀 Next step: cd {output} && ./deploy.sh")
        
    except ConfigurationError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        click.echo(f"❌ Generation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file path')
@click.option('--detailed', is_flag=True, help='Show detailed validation information')
@click.pass_context
def validate(ctx, config: Optional[str], detailed: bool):
    """Validate VectorWeight configuration"""
    
    config_file = config or ctx.obj.get('config_file')
    
    if not config_file:
        click.echo("❌ No configuration file specified", err=True)
        sys.exit(1)
    
    try:
        # Load and validate configuration
        loader = ConfigurationLoader()
        configuration = loader.load_from_file(Path(config_file))
        
        validator = ConfigurationValidator()
        validation_messages = validator.validate(configuration)
        
        # Display results
        click.echo(f"📋 Validating: {configuration.project_name}")
        
        if not validation_messages:
            click.echo("✅ Configuration validation passed!")
            return
        
        # Categorize messages
        errors = [msg for msg in validation_messages if msg.startswith("Error:")]
        warnings = [msg for msg in validation_messages if msg.startswith("Warning:")]
        recommendations = [msg for msg in validation_messages if msg.startswith("Recommendation:")]
        
        # Display summary
        click.echo(f"\n📊 Validation Summary:")
        click.echo(f"   Errors: {len(errors)}")
        click.echo(f"   Warnings: {len(warnings)}")
        click.echo(f"   Recommendations: {len(recommendations)}")
        
        if detailed or errors:
            if errors:
                click.echo(f"\n❌ Errors ({len(errors)}):")
                for error in errors:
                    click.echo(f"   {error}")
            
            if warnings and detailed:
                click.echo(f"\n⚠️  Warnings ({len(warnings)}):")
                for warning in warnings:
                    click.echo(f"   {warning}")
            
            if recommendations and detailed:
                click.echo(f"\nℹ️  Recommendations ({len(recommendations)}):")
                for rec in recommendations:
                    click.echo(f"   {rec}")
        
        if errors:
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file path')
@click.option('--deployment-dir', '-d', type=click.Path(exists=True),
              help='Deployment directory path')
@click.option('--wait', is_flag=True, help='Wait for deployment completion')
@click.pass_context
def deploy(ctx, config: Optional[str], deployment_dir: Optional[str], wait: bool):
    """Deploy VectorWeight homelab to Kubernetes"""
    
    if not deployment_dir:
        deployment_dir = "./vectorweight-deployment"
    
    deployment_path = Path(deployment_dir)
    deploy_script = deployment_path / "deploy.sh"
    
    if not deploy_script.exists():
        click.echo(f"❌ Deploy script not found: {deploy_script}")
        click.echo("💡 Run 'vectorweight generate' first to create deployment")
        sys.exit(1)
    
    try:
        import subprocess
        
        click.echo("🚀 Deploying VectorWeight homelab...")
        
        # Execute deployment script
        result = subprocess.run(
            [str(deploy_script)],
            cwd=deployment_path,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            click.echo("✅ Deployment initiated successfully!")
            if wait:
                click.echo("⏳ Monitoring deployment progress...")
                _monitor_deployment_progress()
        else:
            click.echo("❌ Deployment failed!")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Deployment execution failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--format', type=click.Choice(['table', 'json', 'yaml']), 
              default='table', help='Output format')
def examples():
    """Show example configurations"""
    
    if click.get_current_context().params['format'] == 'table':
        click.echo("📋 Available Configuration Examples:\n")
        
        for name, config in EXAMPLE_CONFIGURATIONS.items():
            click.echo(f"🔧 {name}")
            click.echo(f"   Project: {config.get('project_name', 'N/A')}")
            click.echo(f"   Environment: {config.get('environment', 'N/A')}")
            click.echo(f"   Deployment Mode: {config.get('deployment_mode', 'N/A')}")
            click.echo(f"   Clusters: {len(config.get('clusters', []))}")
            click.echo()
        
        click.echo("💡 Use 'vectorweight init --template <name>' to create configuration")
        
    elif click.get_current_context().params['format'] == 'json':
        click.echo(json.dumps(EXAMPLE_CONFIGURATIONS, indent=2, default=str))
        
    elif click.get_current_context().params['format'] == 'yaml':
        click.echo(yaml.dump(EXAMPLE_CONFIGURATIONS, default_flow_style=False))


@cli.command()
@click.option('--namespace', default='argocd', help='Argo CD namespace')
def status(namespace: str):
    """Check VectorWeight deployment status"""
    
    try:
        import subprocess
        
        click.echo("📊 VectorWeight Deployment Status\n")
        
        # Check if kubectl is available
        try:
            subprocess.run(['kubectl', 'version', '--client'], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            click.echo("❌ kubectl not found. Please install kubectl to check status.")
            sys.exit(1)
        
        # Check Argo CD deployment
        click.echo("🎯 Argo CD Status:")
        result = subprocess.run([
            'kubectl', 'get', 'pods', '-n', namespace, 
            '-l', 'app.kubernetes.io/name=argocd-server'
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            click.echo("✅ Argo CD is running")
        else:
            click.echo("❌ Argo CD not found")
        
        # Check applications
        click.echo("\n📦 Applications:")
        result = subprocess.run([
            'kubectl', 'get', 'applications', '-n', namespace
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                for line in lines[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 3:
                        name, health, sync = parts[0], parts[1], parts[2]
                        status_icon = "✅" if health == "Healthy" and sync == "Synced" else "⚠️"
                        click.echo(f"   {status_icon} {name}: {health}/{sync}")
            else:
                click.echo("   No applications found")
        else:
            click.echo("   Unable to check applications")
            
    except Exception as e:
        click.echo(f"❌ Status check failed: {e}", err=True)


def _interactive_configuration_wizard() -> VectorWaveConfiguration:
    """Interactive configuration wizard"""
    
    click.echo("🧙 VectorWeight Configuration Wizard\n")
    
    # Project basics
    project_name = click.prompt("Project name", default="vectorweight-homelab")
    environment = click.prompt("Environment", 
                             type=click.Choice(['development', 'staging', 'production']),
                             default='production')
    
    # Deployment mode
    deployment_mode = click.prompt("Deployment mode",
                                 type=click.Choice(['internet', 'airgapped-vc', 'airgapped-local']),
                                 default='internet')
    
    # Cluster configuration
    click.echo("\n📦 Cluster Configuration:")
    clusters = []
    
    while True:
        cluster_name = click.prompt("Cluster name (or 'done' to finish)")
        if cluster_name.lower() == 'done':
            break
            
        domain = click.prompt(f"Domain for {cluster_name}", 
                            default=f"{cluster_name}.vectorweight.com")
        
        size = click.prompt("Cluster size",
                          type=click.Choice(['minimal', 'small', 'medium', 'large']),
                          default='small')
        
        gpu_enabled = click.confirm("Enable GPU support?", default=False)
        
        vector_store = click.prompt("Vector store",
                                  type=click.Choice(['disabled', 'weaviate', 'qdrant', 'chroma']),
                                  default='disabled')
        
        cerbos_enabled = click.confirm("Enable Cerbos authorization?", default=False)
        
        cluster_config = {
            "name": cluster_name,
            "domain": domain,
            "size": size,
            "gpu_enabled": gpu_enabled,
            "vector_store": vector_store,
            "cerbos_enabled": cerbos_enabled,
            "specialized_workloads": []
        }
        
        clusters.append(cluster_config)
    
    if not clusters:
        # Default cluster
        clusters.append({
            "name": "dev",
            "domain": "dev.vectorweight.com",
            "size": "small"
        })
    
    # GitHub settings
    github_org = click.prompt("GitHub organization", default="vectorweight")
    auto_create_repos = click.confirm("Auto-create GitHub repositories?", default=True)
    
    config_data = {
        "project_name": project_name,
        "environment": environment,
        "deployment_mode": deployment_mode,
        "clusters": clusters,
        "github_organization": github_org,
        "auto_create_repositories": auto_create_repos
    }
    
    loader = ConfigurationLoader()
    return loader.load_from_dict(config_data)


def _monitor_deployment_progress():
    """Monitor Argo CD deployment progress"""
    import subprocess
    import time
    
    try:
        for _ in range(30):  # Monitor for 5 minutes
            result = subprocess.run([
                'kubectl', 'get', 'applications', '-n', 'argocd', '--no-headers'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                healthy_count = 0
                total_count = len([l for l in lines if l.strip()])
                
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3 and parts[1] == "Healthy" and parts[2] == "Synced":
                            healthy_count += 1
                
                click.echo(f"📊 Applications: {healthy_count}/{total_count} healthy")
                
                if healthy_count == total_count and total_count > 0:
                    click.echo("✅ All applications are healthy!")
                    break
            
            time.sleep(10)
    
    except KeyboardInterrupt:
        click.echo("\n⏹️  Monitoring stopped by user")
    except Exception as e:
        click.echo(f"❌ Monitoring failed: {e}")


if __name__ == '__main__':
    cli()
