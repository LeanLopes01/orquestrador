import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { contextBridge } from './services/context-bridge.mjs';
import { jarvisBridge } from './services/jarvis-bridge.mjs';
import { ragBridge } from './services/rag-bridge.mjs';
import { ingestionBridge } from './services/ingestion-bridge.mjs';
import { auditsBridge } from './services/audits-bridge.mjs';
import { systemBridge } from './services/system-bridge.mjs';
export default defineConfig({ plugins: [react(),systemBridge(),contextBridge(),jarvisBridge(),...ragBridge(),ingestionBridge(),auditsBridge()], server: { host: '127.0.0.1', port: 1420, strictPort: true, watch: { ignored: ['**/src-tauri/**','**/.local/**','**/.venv-rag/**','**/documentacao_rag/**','**/airllm-main/**','**/services/**/src/**','**/test-results/**','**/playwright-report/**'] } }, preview: { host: '127.0.0.1', port: 1420, strictPort: true }, clearScreen: false });
