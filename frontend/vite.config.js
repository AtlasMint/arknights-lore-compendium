import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/graph': 'http://127.0.0.1:5001' } }, // Flask, see backend/app.py
})
