# 自动化部署流程设计（CI/CD）

## 整体架构

基于 GitHub Actions 实现全链路自动化部署，覆盖代码提交 -> 测试 -> 构建 -> 部署 -> 验证 全流程，支持多环境部署和一键回滚。

```
┌─────────────┐
│  开发者提交  │
│  Git Push   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  触发工作流  │ GitHub Actions
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   代码检查   │ ESLint / Prettier
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   单元测试   │ Jest / Pytest
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   集成测试   │ 启动服务进行API测试
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   镜像构建   │ Docker Build & Push
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  部署到环境  │ Dev → Staging → Production (手动确认)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   健康检查   │ 服务可用性验证
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   完成通知   │ Slack / 飞书通知
└─────────────┘
```

## 环境划分

| 环境 | 触发方式 | 域名 | 说明 |
|------|----------|------|------|
| dev | 推任意分支自动触发 | dev.example.com | 开发环境，供开发测试 |
| staging | 合并到main自动触发 | staging.example.com | 预发布环境，验证上线前功能 |
| production | 手动点击确认发布 | example.com | 生产环境，用户访问 |

## GitHub Actions 配置示例

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ '**' ]
  workflow_dispatch:
    inputs:
      environment:
        description: '部署环境'
        required: true
        default: 'dev'

jobs:
  # 1. 代码质量检查
  lint:
    name: 🔍 Code Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run format:check

  # 2. 单元测试
  test-unit:
    name: 🧪 Unit Tests
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run test:unit
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage/

  # 3. 集成测试
  test-integration:
    name: 🧪 Integration Tests
    needs: test-unit
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run test:integration

  # 4. 构建Docker镜像
  build:
    name: 🐳 Build Image
    needs: test-integration
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.event.inputs.environment == 'production'
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - uses: docker/setup-buildx-action@v3
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            yourimage/app:${{ github.sha }}
            yourimage/app:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # 5. 部署到开发环境
  deploy-dev:
    name: 🚀 Deploy to Dev
    needs: build
    if: github.ref != 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - name: 执行部署脚本
        run: ./scripts/deploy.sh dev ${{ github.sha }}

  # 6. 部署到预发布环境
  deploy-staging:
    name: 🚀 Deploy to Staging
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: 执行部署脚本
        run: ./scripts/deploy.sh staging ${{ github.sha }}

  # 7. 部署到生产环境（需要手动确认）
  deploy-production:
    name: 🚀 Deploy to Production
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: 执行部署脚本
        run: ./scripts/deploy.sh production ${{ github.sha }}

  # 8. 健康检查
  health-check:
    name: 🔍 Health Check
    needs: deploy-${{ inputs.environment || 'dev' }}
    runs-on: ubuntu-latest
    steps:
      - name: Wait for deployment
        uses: action-utils/wait-for-url@v1
        with:
          url: https://${{ env.DOMAIN }}/health
          timeout: 300
          interval: 10
      
      - name: Check response
        run: |
          STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://${{ env.DOMAIN }}/health)
          if [ $STATUS -ne 200 ]; then
            echo "Health check failed with status $STATUS"
            exit 1
          fi

  # 9. 发送通知
  notify:
    name: 📢 Notify
    needs: health-check
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Send to Feishu
        uses: rx-rs/feishu-action@main
        with:
          webhook: ${{ secrets.FEISHU_WEBHOOK }}
          status: ${{ job.status }}
```

## 回滚机制

### 自动回滚
- 如果健康检查失败，**自动触发回滚**到上一个稳定版本
- 在部署脚本中实现：如果健康检查不通过，自动切换流量到上一个版本

### 手动回滚
提供一键回滚脚本：
```bash
./scripts/rollback.sh production <version-tag>
```

回滚步骤：
1. 记录当前版本号
2. 切换流量到指定历史版本
3. 等待健康检查通过
4. 发送通知结果

## 部署脚本核心逻辑（示例）

```bash
#!/bin/bash
# deploy.sh <environment> <version>

ENV=$1
VERSION=$2

# 1. 拉取镜像
docker pull yourimage/app:$VERSION

# 2. 更新docker-compose配置
sed -i "s/APP_VERSION=.*/APP_VERSION=$VERSION/g" .env.$ENV

# 3. 滚动更新
docker-compose -f docker-compose.$ENV.yml up -d --no-deps app

# 4. 等待服务启动
sleep 30

# 5. 健康检查
if ! curl -f http://localhost/health; then
  echo "❌ Health check failed"
  ./scripts/rollback.sh $ENV
  exit 1
fi

echo "✅ Deployment successful"
```

## 最佳实践

1. **保护生产环境**：生产环境部署必须手动确认，不能自动触发
2. **缓存依赖**：在GitHub Actions中缓存node_modules或pip依赖，加速构建
3. **镜像分层**：Docker构建使用分层缓存，减少构建时间
4. **不可变镜像**：一个版本只构建一次镜像，各个环境复用同一个镜像，保证一致性
5. **滚动更新**：使用滚动更新不中断服务，用户无感知
6. **观测优先**：部署后必须做健康检查，失败自动回滚
7. **审计日志**：记录每一次部署的版本、执行人、时间，便于追踪问题

---
设计由 oc-coze 于 2026-03-16 生成
