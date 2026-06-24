import { defineConfig } from 'astro/config';

// Static multi-quiz "book study" hub. Outputs plain static files to dist/.
export default defineConfig({
  site: 'https://book-study.sam.ink',
  build: { format: 'directory' },
});
