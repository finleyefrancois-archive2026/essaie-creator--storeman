import { resolve } from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  root: 'src/renderer',
  base: './',
  build: {
    outDir: '../../dist/renderer',
    emptyOutDir: true
  },
  publicDir: false,
  resolve: {
    alias: {
      '@renderer': resolve(__dirname, 'src/renderer')
    }
  }
});
