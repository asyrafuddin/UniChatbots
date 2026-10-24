import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // "@/..." points at src/ — needed for components added with the shadcn CLI (React Bits).
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, 'src') },
  },
})
