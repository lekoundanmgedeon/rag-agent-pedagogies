import type { NextConfig } from "next";

/**
 * L'API est jointe via un chemin relatif `/api/...` en développement comme en
 * production : le navigateur ne connaît jamais l'URL du backend. Cela évite
 * d'avoir à ouvrir CORS et permet au cookie de session de rester `SameSite`.
 *
 * En production, nginx fait la même redirection (cf. agent-tuteur-deploy/).
 */
const nextConfig: NextConfig = {
  async rewrites() {
    const api = process.env.API_ORIGIN ?? "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/health", destination: `${api}/health` },
    ];
  },
};

export default nextConfig;
