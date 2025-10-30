
Hugo + PaperMod Blog
====================

This repository hosts the personal blog of Xin Sky Li, powered by Hugo and the PaperMod theme.

Local development
- Install Hugo Extended (v0.125+).
- Run `hugo server -D` and open http://localhost:1313.

Write posts
- Create files under `content/posts/` with front matter:
  ```
  ---
  title: "My First Post"
  date: 2025-03-01T10:00:00+08:00
  tags: [LLM, Agents]
  categories: [Notes]
  draft: false
  ---
  ```

Deploy
- GitHub Actions builds and deploys on push to `main` using `.github/workflows/deploy-pages.yml`.
- Ensure GitHub Pages is set to “GitHub Actions” as the source in repository Settings → Pages.

Assets
- Static files are served from `static/`, and also from existing folders `images/` and `videos/`.

Notes
- The previous Jekyll setup has been removed in favor of Hugo.
