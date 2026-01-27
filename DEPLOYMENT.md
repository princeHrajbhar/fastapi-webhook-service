# Deployment Guide

This guide covers deploying the FastAPI Webhook Service to production environments.

## Prerequisites

- Docker and Docker Compose
- Secure secret management system
- Monitoring infrastructure (Prometheus, Grafana)
- Log aggregation system (ELK, Loki, CloudWatch)

## Environment Configuration

### Required Environment Variables

```bash
# REQUIRED: HMAC secret for signature verification
WEBHOOK_SECRET=<strong-random-secret>

# Database path (default: sqlite:////data/app.db)
DATABASE_URL=sqlite:////data/app.db

# Logging level (default: INFO)
LOG_LEVEL=INFO
```

### Generating Secure Secrets

```bash
# Generate a strong random secret
openssl rand -hex 32

# Or using Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Create production docker-compose.yml:**

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: fastapi-webhook-service
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:////data/app.db
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/data
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

2. **Deploy:**

```bash
# Set environment variables
export WEBHOOK_SECRET=$(openssl rand -hex 32)

# Start service
docker compose up -d --build

# Verify deployment
curl http://localhost:8000/health/ready
```

### Using Docker Run

```bash
# Build image
docker build -t fastapi-webhook-service:latest .

# Run container
docker run -d \
  --name fastapi-webhook-service \
  -p 8000:8000 \
  -e WEBHOOK_SECRET=$(openssl rand -hex 32) \
  -e DATABASE_URL=sqlite:////data/app.db \
  -e LOG_LEVEL=INFO \
  -v $(pwd)/data:/data \
  --restart always \
  fastapi-webhook-service:latest
```

## Kubernetes Deployment

### 1. Create Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: webhook-secret
type: Opaque
stringData:
  webhook-secret: <your-secret-here>
```

```bash
kubectl apply -f secret.yaml
```

### 2. Create Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-webhook-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-webhook-service
  template:
    metadata:
      labels:
        app: fastapi-webhook-service
    spec:
      containers:
      - name: api
        image: fastapi-webhook-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: WEBHOOK_SECRET
          valueFrom:
            secretKeyRef:
              name: webhook-secret
              key: webhook-secret
        - name: DATABASE_URL
          value: "sqlite:////data/app.db"
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: data
          mountPath: /data
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: webhook-data-pvc
```

### 3. Create Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi-webhook-service
spec:
  selector:
    app: fastapi-webhook-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 4. Create PersistentVolumeClaim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: webhook-data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### 5. Deploy

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f pvc.yaml

# Verify deployment
kubectl get pods
kubectl get svc
```

## Cloud Platform Deployments

### AWS ECS

1. **Build and push image to ECR:**

```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t fastapi-webhook-service .
docker tag fastapi-webhook-service:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/fastapi-webhook-service:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/fastapi-webhook-service:latest
```

2. **Create ECS task definition:**

```json
{
  "family": "fastapi-webhook-service",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/fastapi-webhook-service:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "sqlite:////data/app.db"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "WEBHOOK_SECRET",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:webhook-secret"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health/ready || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Google Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/<project-id>/fastapi-webhook-service

# Deploy
gcloud run deploy fastapi-webhook-service \
  --image gcr.io/<project-id>/fastapi-webhook-service \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=sqlite:////data/app.db,LOG_LEVEL=INFO \
  --set-secrets WEBHOOK_SECRET=webhook-secret:latest \
  --allow-unauthenticated
```

### Azure Container Instances

```bash
# Build and push to ACR
az acr build --registry <registry-name> --image fastapi-webhook-service:latest .

# Deploy
az container create \
  --resource-group <resource-group> \
  --name fastapi-webhook-service \
  --image <registry-name>.azurecr.io/fastapi-webhook-service:latest \
  --dns-name-label fastapi-webhook \
  --ports 8000 \
  --environment-variables DATABASE_URL=sqlite:////data/app.db LOG_LEVEL=INFO \
  --secure-environment-variables WEBHOOK_SECRET=<secret>
```

## Monitoring Setup

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'fastapi-webhook'
    scrape_interval: 15s
    static_configs:
      - targets: ['fastapi-webhook-service:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Import the following metrics:

- `rate(http_requests_total[5m])` - Request rate
- `rate(webhook_requests_total{result="created"}[5m])` - Message creation rate
- `rate(webhook_requests_total{result="duplicate"}[5m])` - Duplicate rate
- `rate(webhook_requests_total{result="invalid_signature"}[5m])` - Invalid signature rate
- `histogram_quantile(0.95, request_latency_ms)` - 95th percentile latency

### Alerting Rules

```yaml
groups:
  - name: fastapi-webhook-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: HighInvalidSignatureRate
        expr: rate(webhook_requests_total{result="invalid_signature"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High invalid signature rate"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, request_latency_ms) > 1000
        for: 5m
        annotations:
          summary: "High request latency"
```

## Log Aggregation

### ELK Stack

```yaml
# Filebeat configuration
filebeat.inputs:
  - type: container
    paths:
      - '/var/lib/docker/containers/*/*.log'
    processors:
      - add_docker_metadata: ~
      - decode_json_fields:
          fields: ["message"]
          target: ""
          overwrite_keys: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

### Loki

```yaml
# Promtail configuration
clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: 'container'
```

## Backup and Recovery

### Database Backup

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Copy database
docker cp fastapi-webhook-service:/data/app.db "$BACKUP_DIR/app_$TIMESTAMP.db"

# Compress
gzip "$BACKUP_DIR/app_$TIMESTAMP.db"

# Keep only last 7 days
find "$BACKUP_DIR" -name "app_*.db.gz" -mtime +7 -delete
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * /path/to/backup.sh
```

## Security Considerations

### 1. Secret Management

- Never commit secrets to version control
- Use secret management systems (AWS Secrets Manager, HashiCorp Vault)
- Rotate secrets regularly
- Use different secrets for different environments

### 2. Network Security

- Use HTTPS/TLS in production
- Implement rate limiting
- Use firewall rules to restrict access
- Consider using API gateway

### 3. Database Security

- Regular backups
- Encrypt data at rest
- Limit database access
- Monitor for suspicious activity

### 4. Container Security

- Use minimal base images
- Scan images for vulnerabilities
- Run as non-root user
- Keep dependencies updated

## Performance Tuning

### 1. Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_messages_from ON messages(from_msisdn);
CREATE INDEX idx_messages_ts ON messages(ts);
CREATE INDEX idx_messages_text ON messages(text);
```

### 2. Application Tuning

```python
# Increase worker count
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3. Resource Limits

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker logs fastapi-webhook-service

# Verify environment variables
docker exec fastapi-webhook-service env | grep WEBHOOK_SECRET

# Check health
curl http://localhost:8000/health/ready
```

### High Memory Usage

```bash
# Check container stats
docker stats fastapi-webhook-service

# Increase memory limit
docker update --memory 1g fastapi-webhook-service
```

### Database Issues

```bash
# Check database file
docker exec fastapi-webhook-service ls -lh /data/app.db

# Verify schema
docker exec fastapi-webhook-service sqlite3 /data/app.db ".schema"
```

## Rollback Procedure

```bash
# Tag current version
docker tag fastapi-webhook-service:latest fastapi-webhook-service:backup

# Pull previous version
docker pull fastapi-webhook-service:previous

# Stop current
docker stop fastapi-webhook-service

# Start previous
docker run -d --name fastapi-webhook-service fastapi-webhook-service:previous

# Verify
curl http://localhost:8000/health/ready
```

## Maintenance

### Regular Tasks

- [ ] Monitor metrics and logs daily
- [ ] Review error rates weekly
- [ ] Update dependencies monthly
- [ ] Rotate secrets quarterly
- [ ] Test backups quarterly
- [ ] Review security annually

### Upgrade Procedure

1. Test new version in staging
2. Backup database
3. Deploy new version
4. Monitor for errors
5. Rollback if issues detected
6. Update documentation
