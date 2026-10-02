"""Travel Fare Insights - Streamlit web app."""
import hashlib
import hmac
import os

import numpy as np
import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="Travel Fare Insights", page_icon="🚆", layout="wide")

# ---------- Responsive CSS (stacks columns & shrinks padding on phones) ----------
st.markdown(
    """
<style>
@media (max-width: 768px){
  .block-container{padding:1rem .6rem !important;}
  [data-testid="column"]{min-width:100% !important;}
  h1{font-size:1.5rem !important;}
}
</style>""",
    unsafe_allow_html=True,
)

# ---------- Security: password gate (SHA-256 hash, constant-time compare) ----------
def check_login() -> bool:
    """Password hash comes from st.secrets or env var APP_PASSWORD_SHA256.
    Demo fallback password: 'travel123' (change before deploying!)."""
    demo = hashlib.sha256(b"travel123").hexdigest()
    try:
        expected = st.secrets["APP_PASSWORD_SHA256"]
    except Exception:
        expected = os.environ.get("APP_PASSWORD_SHA256", demo)
    if st.session_state.get("auth"):
        return True
    st.title("🔒 Travel Fare Insights")
    pw = st.text_input("Password", type="password")
    if st.button("Log in"):
        if hmac.compare_digest(hashlib.sha256(pw.encode()).hexdigest(), expected):
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not check_login():
    st.stop()

# ---------- Data ----------
CITIES = {  # name: (lat, lon)
    "Kochi": (9.93, 76.27), "Thiruvananthapuram": (8.52, 76.94),
    "Chennai": (13.08, 80.27), "Bengaluru": (12.97, 77.59),
    "Mumbai": (19.08, 72.88), "Delhi": (28.61, 77.21),
    "Kolkata": (22.57, 88.36), "Hyderabad": (17.39, 78.49),
}


def haversine(a, b):
    la1, lo1, la2, lo2 = map(np.radians, [a[0], a[1], b[0], b[1]])
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(h))


@st.cache_data(show_spinner="Generating sample data…")
def make_sample(n: int = 20000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    names = list(CITIES)
    o = rng.choice(names, n)
    d = rng.choice(names, n)
    keep = o != d
    o, d = o[keep], d[keep]
    dist = np.array([haversine(CITIES[a], CITIES[b]) for a, b in zip(o, d)])
    cls = rng.choice(["Sleeper", "3AC", "2AC", "1AC"], len(o), p=[.45, .3, .18, .07])
    mult = pd.Series(cls).map({"Sleeper": 1, "3AC": 2.2, "2AC": 3, "1AC": 5}).to_numpy()
    adv = rng.integers(0, 120, len(o))
    fare = dist * 0.6 * mult * (1 + 0.25 * np.exp(-adv / 15)) + rng.normal(0, 40, len(o))
    return pd.DataFrame({
        "date": pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, len(o)), "D"),
        "origin": o, "destination": d, "travel_class": cls,
        "distance_km": dist.round(0), "advance_days": adv,
        "fare": np.clip(fare, 50, None).round(0),
    })


@st.cache_data(show_spinner="Loading file…")
def load_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file, parse_dates=["date"])
    need = {"date", "origin", "destination", "travel_class", "distance_km", "advance_days", "fare"}
    if not need <= set(df.columns):
        raise ValueError(f"CSV must contain columns: {sorted(need)}")
    return df.dropna(subset=list(need))


# ---------- Sidebar ----------
st.sidebar.header("⚙️ Controls")
up = st.sidebar.file_uploader("Upload your own fares CSV (optional)", type="csv")
try:
    df = load_csv(up) if up else make_sample()
except Exception as e:
    st.sidebar.error(str(e))
    df = make_sample()

classes = st.sidebar.multiselect("Travel class", sorted(df.travel_class.unique()),
                                 default=sorted(df.travel_class.unique()))
origin = st.sidebar.selectbox("Origin", ["All"] + sorted(df.origin.unique()))
fmin, fmax = int(df.fare.min()), int(df.fare.max())
fare_rng = st.sidebar.slider("Fare range (₹)", fmin, fmax, (fmin, fmax))
dates = st.sidebar.date_input("Date range", (df.date.min().date(), df.date.max().date()))
search = st.sidebar.text_input("Destination contains…")
if st.sidebar.button("Log out"):
    st.session_state["auth"] = False
    st.rerun()

f = df[df.travel_class.isin(classes) & df.fare.between(*fare_rng)]
if origin != "All":
    f = f[f.origin == origin]
if search:
    f = f[f.destination.str.contains(search, case=False, na=False)]
if len(dates) == 2:
    f = f[(f.date >= pd.Timestamp(dates[0])) & (f.date <= pd.Timestamp(dates[1]))]

# ---------- Main ----------
st.title("🚆 Travel Fare Insights")
if f.empty:
    st.warning("No data matches your filters. Try widening them.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Trips", f"{len(f):,}")
c2.metric("Avg fare", f"₹{f.fare.mean():,.0f}")
c3.metric("Avg ₹/km", f"{(f.fare / f.distance_km).mean():.2f}")
c4.metric("Avg booking lead", f"{f.advance_days.mean():.0f} days")

tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "🗺️ Routes map", "🔎 Explore", "📘 Docs"])

with tab1:
    a, b = st.columns(2)
    m = f.set_index("date").resample("W").fare.mean().reset_index()
    a.plotly_chart(px.line(m, x="date", y="fare", title="Average weekly fare",
                           labels={"fare": "Avg fare (₹)", "date": "Week"}),
                   use_container_width=True)
    b.plotly_chart(px.box(f, x="travel_class", y="fare", color="travel_class",
                          title="Fare distribution by class",
                          labels={"fare": "Fare (₹)", "travel_class": "Class"}),
                   use_container_width=True)
    adv = f.assign(bucket=pd.cut(f.advance_days, [-1, 7, 14, 30, 60, 120],
                                 labels=["0-7", "8-14", "15-30", "31-60", "61+"]))
    adv = adv.groupby("bucket", observed=True).fare.mean().reset_index()
    st.plotly_chart(px.bar(adv, x="bucket", y="fare", title="Does booking early save money?",
                           labels={"bucket": "Days booked in advance", "fare": "Avg fare (₹)"}),
                    use_container_width=True)

with tab2:
    top_n = st.slider("Number of busiest routes to draw", 5, 40, 15)
    r = (f.groupby(["origin", "destination"]).agg(trips=("fare", "size"), avg_fare=("fare", "mean"))
         .reset_index().nlargest(top_n, "trips"))
    r["s_lat"], r["s_lon"] = r.origin.map(lambda x: CITIES.get(x, (0, 0))[0]), r.origin.map(lambda x: CITIES.get(x, (0, 0))[1])
    r["d_lat"], r["d_lon"] = r.destination.map(lambda x: CITIES.get(x, (0, 0))[0]), r.destination.map(lambda x: CITIES.get(x, (0, 0))[1])
    r["avg_fare"] = r.avg_fare.round(0)
    layer = pdk.Layer("ArcLayer", r, get_source_position=["s_lon", "s_lat"],
                      get_target_position=["d_lon", "d_lat"], get_width="trips / 20 + 1",
                      get_source_color=[0, 128, 255], get_target_color=[255, 80, 80], pickable=True)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=pdk.ViewState(latitude=17, longitude=79, zoom=3.5),
                             tooltip={"text": "{origin} → {destination}\nTrips: {trips}\nAvg fare: ₹{avg_fare}"}))
    st.caption("Hover an arc for details. Arc thickness = number of trips.")

with tab3:
    sample = f.sample(min(len(f), 3000), random_state=1)  # cap points for speed
    st.plotly_chart(px.scatter(sample, x="distance_km", y="fare", color="travel_class",
                               hover_data=["origin", "destination", "advance_days"],
                               title="Fare vs distance (3,000-point sample)",
                               labels={"distance_km": "Distance (km)", "fare": "Fare (₹)"}),
                    use_container_width=True)
    st.dataframe(f.head(500), use_container_width=True)
    st.download_button("Download filtered data", f.to_csv(index=False), "filtered_fares.csv", "text/csv")

with tab4:
    st.markdown(open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8").read()
                if os.path.exists(os.path.join(os.path.dirname(__file__), "README.md")) else "See README.md")
