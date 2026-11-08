# Fix: Season dropdown is empty / Unable to load season

The season dropdown is static but the Grand Prix dropdown is populated from the backend `/api/seasons/{year}/races` route. If it is empty, that request failed; the frontend alone cannot populate it.

## Run two separate PowerShell terminals

Terminal 1 (inside `backend`):
```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Check these URLs in a browser:
- http://127.0.0.1:8000/api/health — should return JSON with `status: ok`
- http://127.0.0.1:8000/api/seasons/2024/races — should return a non-empty JSON array.

Terminal 2 (inside `frontend`):
```powershell
npm install
npm run dev
```

Open http://127.0.0.1:5173 and refresh. Restart the Vite process after changing `vite.config.ts`.

V6.2 uses a relative `/api` prefix and Vite proxy pointing to `http://127.0.0.1:8000`; this avoids hardcoding the backend hostname in browser requests. The displayed API status is now based on a health check, not a static label.

If the health endpoint works but the season endpoint gives HTTP 502, the backend is running but cannot retrieve the Jolpica schedule (network connection, DNS, provider availability). Check terminal 1 and the JSON error details. The OpenF1 benchmark succeeding does not confirm that Jolpica requests succeed.

If port 8000 is already occupied, stop the older backend process before starting the new one.

Production deployment needs a reverse proxy for `/api`; Vite's proxy only applies to local development.
