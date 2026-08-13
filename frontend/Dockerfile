# LightWMS Frontend Dockerfile
# Multi-stage build for Next.js production deployment

# ============================================
# Stage 1: Dependencies
# ============================================
FROM node:22-alpine AS deps

WORKDIR /app

RUN npm config set registry https://registry.npmmirror.com

COPY package*.json ./
RUN npm ci --legacy-peer-deps

# ============================================
# Stage 2: Builder
# ============================================
FROM node:22-alpine AS builder

WORKDIR /app

RUN npm config set registry https://registry.npmmirror.com

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Cookie security is intentionally a runtime setting. Do not bake HTTP/HTTPS
# policy into the standalone bundle during image build.
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
ENV BUILD_STANDALONE=true

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

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/login/ || exit 1

CMD ["node", "server.js"]
