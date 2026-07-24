import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// L'API FastAPI tourne par défaut sur :8000 (cf. agent-tuteur-api). On proxifie
// /api et /health en dev pour éviter tout souci CORS et pour que le streaming
// SSE (fetch) passe de façon transparente. Surchargeable via VITE_API_TARGET.
const API_TARGET = process.env.VITE_API_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
      '/health': { target: API_TARGET, changeOrigin: true },
    },
  },
})
