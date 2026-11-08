# GitHub publication checklist

1. Keep the original `steering_data/` directory and three `.pt` checkpoints **local**. Never commit licensed F1 video frames, `.env` credentials or full local audit CSVs containing absolute filesystem paths.
2. Verify `npm run build` in `frontend/` and `python -m pytest -q` in `backend/` on your computer.
3. Run `git status --short` and `git diff --cached --name-only` before pushing. If `steering_data/`, local image files, or `.pt` files appear, **stop** and remove them from the index.
4. Repository name suggestion: `f1-performance-lab`. Set it **Public** and do not initialize a duplicate README or .gitignore on GitHub.
5. After publishing, check the GitHub Actions workflow and the rendered README. Be transparent: steering Experiment 01 has known train/validation leakage and source groups remain unverified.
6. Linking a GitHub repository in an application is optional unless the form requires it. Submit the application before the deadline even if deployment or follow-up model training is unfinished.

Do not publish any dataset or screenshots derived from rights-restricted video unless permission is established. The static frontend alone is not a fully deployed project without a hosted backend.
