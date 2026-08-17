import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: './' 让构建产物用相对路径，可部署到 GitHub Pages 的子路径
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
  },
})
