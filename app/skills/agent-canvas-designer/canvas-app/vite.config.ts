import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    port: 5173,
    open: false,
    proxy: {
      '/events': 'http://localhost:8081',
      '/save-config': 'http://localhost:8081',
      '/save-feedback': 'http://localhost:8081',
      '/get-state': 'http://localhost:8081',
      '/config.json': 'http://localhost:8081',
    },
  },
});
