import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// On Windows + Docker driver, Minikube NodePorts aren't directly accessible.
// Use `npm run proxy` in a separate terminal to forward the API server port.
// The proxy command: kubectl port-forward -n autoscaler svc/api-server-service 8000:8000
const apiTarget = 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        // If port-forward is down, show a nicer error
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.error('[vite-proxy] API server unreachable. Run: npm run proxy')
          })
        },
      },
      '/health': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
