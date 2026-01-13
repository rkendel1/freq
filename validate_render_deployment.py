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
        
        # Validate basic structure
        if not config or 'services' not in config:
            print("✗ render.yaml missing 'services' key")
            return False
        
        if not isinstance(config['services'], list) or len(config['services']) == 0:
            print("✗ render.yaml has no services defined")
            return False
        
        service = config['services'][0]
        
        # Check required fields exist
        if service.get('type') != 'web':
            print("✗ Service type must be 'web'")
            return False
        
        if service.get('env') != 'docker':
            print("✗ Service environment must be 'docker'")
            return False
        
        if service.get('dockerfilePath') != './Dockerfile.dev':
            print("✗ Dockerfile path must be './Dockerfile.dev'")
            return False
        
        if service.get('healthCheckPath') != '/health':
            print("✗ Health check path must be '/health'")
            return False
        
        if 'disk' not in service:
            print("✗ Persistent disk configuration missing")
            return False
        
        if service['disk'].get('mountPath') != '/freqtrade/user_data':
            print("✗ Disk mount path must be '/freqtrade/user_data'")
            return False
        
        # Check that PORT is NOT explicitly defined (Render provides it automatically)
        env_vars = service.get('envVars', [])
        if not isinstance(env_vars, list):
            print("✗ envVars must be a list")
            return False
        
        for var in env_vars:
            if not isinstance(var, dict) or 'key' not in var:
                print("✗ Invalid environment variable entry (missing 'key')")
                return False
            if var['key'] == 'PORT':
                print("✗ render.yaml should not define PORT (Render provides it automatically)")
                return False
        
        print("✓ render.yaml configuration is valid")
        print("✓ PORT is not explicitly defined (Render will provide it)")
        return True
        
    except yaml.YAMLError as e:
        print(f"✗ YAML syntax error in render.yaml: {e}")
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
    
    print("🚨 IMPORTANT: Service MUST be configured as Docker")
    print("   If you see 'No open ports detected' error:")
    print("   → Your service is misconfigured as Python instead of Docker")
    print("   → See RENDER_FIX.md for step-by-step fix instructions")
    print()
    
    results = []
    
    # Check required files
    print("Checking required files...")
    results.append(check_file_exists('render.yaml', 'Render Blueprint'))
    results.append(check_file_exists('Dockerfile.dev', 'Development Dockerfile'))
    results.append(check_file_exists('docker/entrypoint.sh', 'Entrypoint script'))
    results.append(check_file_exists('docker/supervisord.conf', 'Supervisord config'))
    results.append(check_file_exists('RENDER_DEPLOYMENT.md', 'Deployment documentation'))
    results.append(check_file_exists('RENDER_FIX.md', 'Render troubleshooting guide'))
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
        print()
        print("📋 Deployment Checklist:")
        print("   1. Use 'New' → 'Blueprint' in Render Dashboard")
        print("   2. Connect GitHub repository")
        print("   3. Verify service is created as 'Docker' environment")
        print("   4. DO NOT create as Python service")
        print("   5. Set STREAMLIT_PASSWORD in environment variables")
        print()
        return 0
    else:
        failed = results.count(False)
        print(f"✗ {failed} validation check(s) failed")
        print("✗ Please fix the issues before deploying")
        return 1

if __name__ == '__main__':
    sys.exit(main())
