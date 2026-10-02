# 🚆 Travel Fare Insights – Documentation

## Run it
```bash
pip install -r requirements.txt
streamlit run app.py
```
Demo password: `travel123` (change it – see *Security*).

## Data source
- **Default:** a synthetic dataset of ~20,000 train trips between 8 Indian cities (seeded, so reproducible). Fares rise with distance and class, and are higher for last-minute bookings.
- **Your own data:** upload a CSV in the sidebar with columns
  `date, origin, destination, travel_class, distance_km, advance_days, fare`.
  To use the earlier train-fares dataset, rename its columns to match. Origins/destinations must be in the `CITIES` dict in `app.py` to appear on the map.

## Preprocessing
1. Dates parsed to datetime; rows with missing required fields dropped.
2. Synthetic distances computed with the haversine formula from city coordinates.
3. Fares clipped to a minimum of ₹50 (removes negative noise).
4. Weekly averages via resampling; advance-booking days grouped into buckets (0-7, 8-14, 15-30, 31-60, 61+).

## Visualizations and what they tell you
| Chart | Insight |
|---|---|
| KPI tiles | Quick summary of the current filter: trips, average fare, ₹/km, booking lead time |
| Weekly fare line | Seasonality and trends over time |
| Box plot by class | Spread, median and outliers per class |
| Advance-booking bars | Whether booking early lowers fares |
| Route arc map | Busiest routes; arc width = trip count; hover for average fare |
| Scatter (fare vs distance) | How strongly distance drives price; hover for route details |

## Interactivity
Sidebar filters (class, origin, fare slider, date range, destination text search), a slider for number of routes on the map, CSV upload and download of filtered data.

## Performance
- `@st.cache_data` on data generation and CSV loading.
- Scatter plot capped at 3,000 sampled points; table shows first 500 rows.
- Aggregation happens before plotting (maps/bars use grouped data, not raw rows).
- Tabs render only their own content, and the app uses no heavy images (so no image compression is needed).

## Responsive design
`layout="wide"` plus CSS media query: on screens ≤768px columns stack vertically and padding shrinks. Plotly charts use `use_container_width=True`. Test by opening the app on a phone (same Wi-Fi, `http://<your-ip>:8501`) or using browser DevTools device mode.

## Security
- Login gate with SHA-256 password hash and constant-time comparison; password is never stored in plain text.
- Set your own password hash:
  `python -c "import hashlib;print(hashlib.sha256(b'YourPassword').hexdigest())"`
  then put `APP_PASSWORD_SHA256 = "<hash>"` in `.streamlit/secrets.toml` (never commit this file) or an environment variable.
- Uploaded files are processed in memory only and not saved.
- Dataset contains no personal data. For real passenger data: anonymise before use, deploy over HTTPS, and use a proper auth provider (e.g. `st.login` with OIDC) instead of a shared password.

## Limitations
Synthetic data shows modelled patterns, not real-world pricing. A single shared password is suitable for demos only.
