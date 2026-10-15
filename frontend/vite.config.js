import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // `npm run dev` talks to a backend started with `uvicorn app.main:app --port 8000`.
    proxy: { '/api': 'http://localhost:8000' },
  },
});
