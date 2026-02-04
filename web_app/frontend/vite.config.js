import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  build: {
    outDir: '../static/dist',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        main: './src/main.js',
        Adashboard: './src/js/Adashboard.js',
        Mdashboard: './src/js/Mdashboard.js',
        dashboard: './src/js/dashboard.js',
        lease: './src/js/lease.js',
        private_requests: './src/js/private_requests.js',
        reports: './src/js/reports.js',
        reservations: './src/js/reservations.js',
        script: './src/js/script.js',
      }
    }
  },
  optimizeDeps: {
    exclude: ['@toast-ui/calendar']
  }
});
