# Docker Build Notes

## Build Environment

The Docker image is designed to run in standard Docker environments. 

### Known Issues in CI/Test Environments

If building in environments with custom CA certificates or proxies, you may encounter SSL verification errors. This is not an issue with the Dockerfile itself, but with the build environment's network configuration.

**Workaround for test environments:**
```dockerfile
# Temporarily disable SSL verification (NOT for production!)
ENV PIP_TRUSTED_HOST=pypi.org pypi.python.org files.pythonhosted.org
```

### Recommended Build Environment

- Standard Docker Desktop (macOS/Windows)
- Docker on Linux with standard network configuration
- Cloud providers with standard Docker support

### Testing the Build

```bash
# On a standard system:
docker build -f Dockerfile.dev -t freqtrade-dev .

# Or use docker compose:
docker compose -f docker-compose.dev.yml build
```

## Build Success Criteria

The build should:
1. ✅ Complete all stages (base, python-deps, runtime)
2. ✅ Install all Python dependencies
3. ✅ Configure supervisor correctly
4. ✅ Set proper file permissions
5. ✅ Create entrypoint with execute permissions

Total build time: ~5-10 minutes (depending on cache)
Final image size: ~1.5-2GB

## Runtime Verification

After building, verify the image works:

```bash
# Test run
docker run --rm freqtrade-dev freqtrade --version

# Full startup test
docker compose -f docker-compose.dev.yml up

# Check all services are running
docker compose -f docker-compose.dev.yml exec freqtrade-dev supervisorctl status
```

Expected output:
```
config_dashboard                 RUNNING   pid 123, uptime 0:00:10
demo_ui                          RUNNING   pid 124, uptime 0:00:10
freqtrade                        RUNNING   pid 125, uptime 0:00:10
monitor_dashboard                RUNNING   pid 126, uptime 0:00:10
```
