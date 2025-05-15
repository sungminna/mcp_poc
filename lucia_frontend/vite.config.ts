import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true,
			},
			// Proxy only the chat WebSocket path to Django Channels
			'/ws/chat': {
				target: 'ws://localhost:8000',
				ws: true,
				changeOrigin: true,
			}
		}
	}
});
