import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL || 'http://backend:8000';

const nextConfig: NextConfig = {
  reactCompiler: true,
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  output: process.env.BUILD_STANDALONE === 'true' ? 'standalone' : undefined,

  // Keep uploads on the same browser origin as the UI. The browser only needs
  // IP:HTTP_PORT; Next.js forwards media requests over the Docker network.
  async rewrites() {
    return [
      {
        source: '/media/:path*',
        destination: `${backendUrl}/media/:path*`,
      },
    ];
  },

  images: {
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
    ],
    unoptimized: process.env.NODE_ENV === 'development',
  },
};

export default nextConfig;
