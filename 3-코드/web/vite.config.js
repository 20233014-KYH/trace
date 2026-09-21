import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api → 참고 서버(dev_receiver.py) 또는 A의 Backend. 개발 중 CORS 없이 쓰기 위한 프록시.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:5000' } },
})
