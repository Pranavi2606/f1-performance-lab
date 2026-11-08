# V10 · Driver debrief, track map and experimental video steering

This upgrade extends **V9**. It includes existing tyre research, results dashboard, and previous circuit fixes.

## Driver Debrief (React sidebar)

Select year, Grand Prix and **Driver Debrief**. Choose a primary driver, one or many comparison drivers, then choose a driver in the *Detail View*. The app compares each driver's fastest **non-pit-out, valid-duration race lap**, which may be on different compounds, fuel loads or weather conditions.

The backend loads public OpenF1 car/lap data, produces approximate progress-aligned speed, throttle, **binary brake**, gear, RPM and relative time traces. Corner-like windows are inferred from braking/throttle patterns on the primary lap. They are not FIA-defined corners or validated vehicle dynamics.

### Track map

The **Track map** section pulls OpenF1 `location` XY samples for the *reference lap*. It displays a circuit-shaped line and pins at the midpoint of the inferred debrief windows. Pins are **Zone 1**, **Zone 2**, etc., not official turn numbers. XY coordinates are approximate and may be noisy. Markers are placed by elapsed-lap fraction; this is not validated spatial distance alignment.

Route: `GET /api/analytics/debrief/track/{year}/{round}/{driver_number}?lap_number=...&zones=5,10;45,52`.

### Report exports

Buttons on the Driver Debrief page produce **Markdown** and **PDF** files containing the session, reference lap, comparison laps, time differences, zone summaries, and limitations. The export uses the current debrief response and deliberately does **not** invent observations.

Routes: `POST /api/analytics/debrief/export/md`, `POST /api/analytics/debrief/export/pdf` with JSON `{ "report": <debrief response> }`.

The PDF engine is **reportlab** (included in `backend/requirements.txt`). A matching Markdown report is generated on demand.

## Experimental steering: a separate, optional module

**This is not a trained, validated steering model.** Public OpenF1 `car_data` has no steering-angle sensor value. We provide a reproducible **image-plane rotation prototype** only, using one visible wheel marker and a fixed center that the user annotates manually. The method is *Lucas-Kanade optical flow*, not a trained steering angle network.

1. Acquire your own onboard/simulator video or video you have a right to process. Do not download or redistribute copyrighted broadcast footage without permission.
2. Identify the wheel center `(cx,cy)` and one easily tracked feature fixed on the wheel `(mx,my)` in the **first video frame**, in pixel coordinates.
3. Install optional OpenCV: `pip install opencv-python` (not a core backend requirement).
4. In the `backend` directory run:

   ```powershell
   python scripts/estimate_steering_video.py --video "C:\path\to\onboard.mp4" --cx 610 --cy 440 --mx 704 --my 445 --output ../results/steering_cv.csv
   ```

5. In **Driver Debrief**, import `steering_cv.csv` into the **Onboard-video steering estimate** panel. The chart uses `video_elapsed_s`; it does **not** overlay or auto-synchronize with real telemetry.

The angle is the **cumulative rotation of a tracked image feature around a chosen pixel location**, not calibrated steering-wheel angle, steering-column angle or front-wheel steer angle. It breaks under camera movement, parallax, occlusion, marker drift, or poor image quality. Its `tracking_only`/`low` flags do not constitute statistical uncertainty calibration. Never use it to claim actual oversteer or real setup characteristics. Validate against labeled footage before calling it an estimated steering angle in a research result.

A synthetic demonstration CSV is available as `results/SYNTHETIC_STEERING_CV.csv`, generated from simple artificially drawn video and **not from any F1 car**.

## Accuracy and code validation

- Backend tests: run `cd backend; python -m pytest -q`
- Production frontend: `cd frontend; npm install; npm run build`
- Live OpenF1 routes and on-board video still require validation on the user's computer with real rights-cleared data.

**Important:** This is a public-data research / driver debrief prototype, not a professional Pi Toolbox replacement. Real driver engineering conclusions require high-quality time/position-aligned channels, setup telemetry and validation beyond the available feeds.
