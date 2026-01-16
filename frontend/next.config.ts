import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  // 保留尾部斜杠，避免 POST 请求重定向丢失 body
  trailingSlash: true,
  // 跳过尾部斜杠重定向对 API 路由的影响
  skipTrailingSlashRedirect: true,
  // 生产环境使用 standalone 模式，便于 Docker 部署
  output: process.env.BUILD_STANDALONE === 'true' ? 'standalone' : undefined,
  // 实验性功能：信任代理头
  experimental: {
    // 允许 Next.js 信任 X-Forwarded-* 头
  },
  // 图片优化配置
  images: {
    // 允许从后端加载图片
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/media/**',
      },
      {
        protocol: 'http',
        hostname: 'backend',
        port: '8000',
        pathname: '/media/**',
      },
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '3000',
        pathname: '/api/media/**',
      },
    ],
    // 允许未优化的图片（用于开发环境）
    unoptimized: process.env.NODE_ENV === 'development',
  },
};

export default nextConfig;
