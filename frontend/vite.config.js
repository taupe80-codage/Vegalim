import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiUrl = env.VITE_API_URL || 'http://localhost:8000'

  return {
    plugins: [react()],

    // ── Proxy développement ─────────────────────────────────────────────────
    // Évite les problèmes CORS en dev : /api/* → backend local
    // En production ce proxy n'existe pas — VITE_API_URL est utilisé directement
    server: {
      proxy: {
        '/auth':        { target: apiUrl, changeOrigin: true },
        '/recettes':    { target: apiUrl, changeOrigin: true },
        '/frigo':       { target: apiUrl, changeOrigin: true },
        '/nutrition':   { target: apiUrl, changeOrigin: true },
        '/planning':    { target: apiUrl, changeOrigin: true },
        '/profil':      { target: apiUrl, changeOrigin: true },
        '/ingredients': { target: apiUrl, changeOrigin: true },
        '/healthz':     { target: apiUrl, changeOrigin: true },
        '/stats':       { target: apiUrl, changeOrigin: true },
      },
    },

    // ── Build production ────────────────────────────────────────────────────
    build: {
      outDir:     'dist',
      sourcemap:  false,         // mettre true si besoin de debug prod
      chunkSizeWarningLimit: 800,
      rollupOptions: {
        output: {
          // Sépare react du code applicatif pour un meilleur cache navigateur
          // Vite 8 (rolldown) requiert une fonction, pas un objet
          manualChunks: (id) => {
            if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
              return 'vendor'
            }
          },
        },
      },
    },
  }
})
