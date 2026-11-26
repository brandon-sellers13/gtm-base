import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The connector's OAuth discovery documents live at fixed addresses under
  // /.well-known; route handlers serve them. Each answers 404 unless the
  // connector is turned on for the site.
  async rewrites() {
    return [
      { source: "/.well-known/oauth-protected-resource", destination: "/api/connector/wk/resource" },
      { source: "/.well-known/oauth-protected-resource/mcp", destination: "/api/connector/wk/resource" },
      { source: "/.well-known/oauth-authorization-server", destination: "/api/connector/wk/as" },
    ];
  },
  // The consent page must never be shown inside another site's frame.
  async headers() {
    return [
      {
        source: "/connect/:path*",
        headers: [
          { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Cache-Control", value: "no-store" },
        ],
      },
    ];
  },
};

export default nextConfig;
