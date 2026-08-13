# LightWMS Frontend Dockerfile
# Multi-stage build for Next.js production deployment

# ============================================
# Stage 1: Dependencies
# ============================================
FROM node:22-alpine AS deps

WORKDIR /app

# 使用淘宝 npm 镜像加速
RUN npm config set registry https://registry.npmmirror.com

# Install dependencies
COPY package*.json ./
RUN npm ci --legacy-peer-deps

# ============================================
# Stage 2: Builder
# ============================================
FROM node:22-alpine AS builder

WORKDIR /app

# 使用淘宝 npm 镜像加速
RUN npm config set registry https://registry.npmmirror.com

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 构建参数：内网 HTTP 部署时设置为 false
ARG SECURE_COOKIES=true

# Build Next.js in standalone mode
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
ENV BUILD_STANDALONE=true
ENV SECURE_COOKIES=${SECURE_COOKIES}

# Build the application (skip type generation in CI)
RUN npm run build:ci

# ============================================
# Stage 3: Production Runner
# ============================================
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy standalone build
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
