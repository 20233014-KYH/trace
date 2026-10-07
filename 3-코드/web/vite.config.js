import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// /api → 참고 서버(dev_receiver.py) 또는 A의 Backend. 개발 중 CORS 없이 쓰기 위한 프록시.
// @ → src  (shadcn/ui · Magic UI · React Bits 가 이 별칭으로 import 한다)
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, './src') } },
  // 포트는 PORT 환경변수가 있으면 그것 (다른 세션이 5173 을 쓰고 있을 때). 밖으로 나가는 프록시만 쓰므로 포트는 아무거나 괜찮다.
  server: { port: Number(process.env.PORT) || 5173, proxy: { '/api': 'http://127.0.0.1:5000' } },
})
