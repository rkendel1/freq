#!/usr/bin/env python3
"""
Validation script for Render deployment configuration.
Checks that all necessary files and configurations are in place.
"""

import os
import sys
import yaml
from pathlib import Path

def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(filepath).exists():
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ Missing {description}: {filepath}")
        return False

def validate_render_yaml() -> bool:
    """Validate render.yaml configuration."""
    try:
        with open('render.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        service = config['services'][0]
        
        # Check required fields
        checks = [
            service['type'] == 'web',
            service['env'] == 'docker',
            service['dockerfilePath'] == './Dockerfile.dev',
            service.get('healthCheckPath') == '/health',
            'disk' in service,
            service['disk']['mountPath'] == '/freqtrade/user_data',
        ]
        
        if all(checks):
            print("✓ render.yaml configuration is valid")
            return True
        else:
            print("✗ render.yaml configuration has issues")
            return False
    except Exception as e:
        print(f"✗ Error validating render.yaml: {e}")
        return False

def validate_dockerfile() -> bool:
    """Validate Dockerfile.dev exists and has required components."""
    try:
        with open('Dockerfile.dev', 'r') as f:
            content = f.read()
        
        required_elements = [
            'FROM python:3.12-slim',
            'WORKDIR /freqtrade',
            'EXPOSE 5000 8501 8502',
            'VOLUME ["/freqtrade/user_data"]',
            'ENTRYPOINT',
        ]
        
        missing = [elem for elem in required_elements if elem not in content]
        
        if not missing:
            print("✓ Dockerfile.dev has all required elements")
            return True
        else:
            print(f"✗ Dockerfile.dev missing: {missing}")
            return False
    except Exception as e:
        print(f"✗ Error validating Dockerfile.dev: {e}")
        return False

def validate_entrypoint() -> bool:
    """Validate entrypoint.sh has PORT handling."""
    try:
        with open('docker/entrypoint.sh', 'r') as f:
            content = f.read()
        
        required_elements = [
            'DEMO_UI_PORT="${PORT:-5000}"',
            'CONFIG_DASHBOARD_PORT=',
            'MONITOR_DASHBOARD_PORT=',
            'export DEMO_UI_PORT',
        ]
        
        missing = [elem for elem in required_elements if elem not in content]
        
        if not missing:
            print("✓ docker/entrypoint.sh has PORT environment variable handling")
            return True
        else:
            print(f"✗ docker/entrypoint.sh missing: {missing}")
            return False
    except Exception as e:
        print(f"✗ Error validating docker/entrypoint.sh: {e}")
        return False

def validate_supervisord() -> bool:
    """Validate supervisord.conf uses environment variables."""
    try:
        with open('docker/supervisord.conf', 'r') as f:
            content = f.read()
        
        required_vars = [
            '%(ENV_DEMO_UI_PORT)s',
            '%(ENV_CONFIG_DASHBOARD_PORT)s',
            '%(ENV_MONITOR_DASHBOARD_PORT)s',
        ]
        
        missing = [var for var in required_vars if var not in content]
        
        if not missing:
            print("✓ docker/supervisord.conf uses environment variables correctly")
            return True
        else:
            print(f"✗ docker/supervisord.conf missing: {missing}")
            return False
    except Exception as e:
        print(f"✗ Error validating docker/supervisord.conf: {e}")
        return False

def main():
    """Run all validation checks."""
    print("=" * 60)
    print("Render Deployment Configuration Validation")
    print("=" * 60)
    print()
    
    results = []
    
    # Check required files
    print("Checking required files...")
    results.append(check_file_exists('render.yaml', 'Render Blueprint'))
    results.append(check_file_exists('Dockerfile.dev', 'Development Dockerfile'))
    results.append(check_file_exists('docker/entrypoint.sh', 'Entrypoint script'))
    results.append(check_file_exists('docker/supervisord.conf', 'Supervisord config'))
    results.append(check_file_exists('RENDER_DEPLOYMENT.md', 'Deployment documentation'))
    results.append(check_file_exists('.renderignore', 'Render ignore file'))
    print()
    
    # Validate configurations
    print("Validating configurations...")
    results.append(validate_render_yaml())
    results.append(validate_dockerfile())
    results.append(validate_entrypoint())
    results.append(validate_supervisord())
    print()
    
    # Summary
    print("=" * 60)
    if all(results):
        print("✓ All validation checks passed!")
        print("✓ Ready for Render deployment")
        return 0
    else:
        failed = results.count(False)
        print(f"✗ {failed} validation check(s) failed")
        print("✗ Please fix the issues before deploying")
        return 1

if __name__ == '__main__':
    sys.exit(main())
