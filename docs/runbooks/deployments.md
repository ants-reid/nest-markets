# Deployment Procedures

## Environments

| Environment | URL | Branch |
|-------------|-----|--------|
| Development | localhost | any |
| Staging | staging.market-hunter.internal | main |
| Production | app.market-hunter.internal | main (tagged) |

## Standard Deployment

### API

```bash
# 1. Run tests
scripts/test/test-api.sh

# 2. Build and tag image
docker build -f infra/docker/Dockerfile.api -t market-hunter-api:$(git rev-parse --short HEAD) .

# 3. Push to registry
docker push market-hunter-api:$(git rev-parse --short HEAD)

# 4. Deploy (Kubernetes / ECS depending on infrastructure)
scripts/deploy/deploy-api.sh

# 5. Run migrations
scripts/db/migrate.sh
```

### Web

```bash
scripts/test/test-web.sh
docker build -f infra/docker/Dockerfile.web -t market-hunter-web:$(git rev-parse --short HEAD) .
scripts/deploy/deploy-web.sh
```

### Learning Pipelines

```bash
scripts/test/test-learning.sh
docker build -f infra/docker/Dockerfile.learning -t market-hunter-learning:$(git rev-parse --short HEAD) .
scripts/deploy/deploy-learning.sh
```

## Rollback

```bash
# Roll back to previous image tag
scripts/deploy/rollback.sh <previous_image_tag>
```

## Post-Deployment Checks

1. API health: `curl http://localhost:8000/health`
2. Grafana **API Latency** dashboard — confirm p95 < 200ms
3. Check error rate on **API Latency** dashboard — confirm < 0.1%
4. Smoke test key endpoints:
   - `GET /models/active`
   - `GET /opportunities`
   - `GET /signals`
