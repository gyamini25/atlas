import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// The webview is built to media/webview with stable asset names so the extension
// host can reference them without parsing hashed filenames.
export default defineConfig({
  root: 'webview',
  plugins: [react()],
  build: {
    outDir: '../media/webview',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/webview.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/webview.[ext]',
      },
    },
  },
});
