"""Cortex AI token monitor: speedometer (tokens/hour) and odometer (running total)."""
import hashlib
import math
import os
import re
from datetime import timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Cortex Token Monitor", page_icon=":material/speed:", layout="wide")
st.title(":material/speed: Cortex AI token monitor")
st.caption(
    "Source: TOKEN.USAGE.CORTEX_TOKEN_USAGE_V (ACCOUNT_USAGE). "
    "Data lags ~45 min to 3 h, so the speedometer reflects the latest available rate."
)

conn = st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))

HOURLY_SQL = """
SELECT DATE_TRUNC('hour', usage_time) AS hr,
       service,
       COALESCE(user_name, '(unattributed)') AS user_name,
       SUM(COALESCE(tokens, 0))  AS tokens,
       SUM(COALESCE(credits, 0)) AS credits
FROM TOKEN.USAGE.CORTEX_TOKEN_USAGE_V
WHERE usage_time IS NOT NULL
GROUP BY 1, 2, 3
"""


@st.cache_data(ttl=600, show_spinner=False)
def load_hourly() -> pd.DataFrame:
    df = conn.query(HOURLY_SQL, ttl=0)
    df.columns = [c.lower() for c in df.columns]
    df["hr"] = pd.to_datetime(df["hr"], utc=True)
    df["tokens"] = df["tokens"].astype(float)
    df["credits"] = df["credits"].astype(float)
    return df


def mask_email_usernames(df: pd.DataFrame) -> pd.DataFrame:
    """Replace email-style usernames with stable, non-identifying display labels."""
    masked = df.copy()
    email_users = sorted(
        name for name in masked["user_name"].dropna().unique()
        if re.fullmatch(r"[^\s@]+@[^\s@]+", str(name))
    )
    labels = {name: f"Email user {i}" for i, name in enumerate(email_users, start=1)}
    masked["user_name"] = masked["user_name"].replace(labels)
    return masked


def clear_cache() -> None:
    load_hourly.clear()


# ---------- visual components (pure SVG/HTML, no extra packages) ----------
def fmt(n: float) -> str:
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return f"{n:,.0f}"


def speedometer(value: float, vmax: float, label: str, size: int = 260) -> str:
    vmax = max(vmax, 1.0)
    frac = min(value / vmax, 1.0)
    cx, cy, r = size / 2, size * 0.55, size * 0.4

    def pt(f: float, rad: float) -> tuple[float, float]:
        a = math.pi * (1 - f)
        return cx + rad * math.cos(a), cy - rad * math.sin(a)

    def arc(f0: float, f1: float, color: str) -> str:
        x0, y0 = pt(f0, r)
        x1, y1 = pt(f1, r)
        return (f'<path d="M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 0 1 {x1:.1f},{y1:.1f}" '
                f'stroke="{color}" stroke-width="{size * 0.07:.1f}" fill="none"/>')

    zones = arc(0, 0.6, "#29B5E8") + arc(0.6, 0.85, "#F5A623") + arc(0.85, 1.0, "#E5484D")
    ticks = ""
    for i in range(11):
        x0, y0 = pt(i / 10, r * 0.78)
        x1, y1 = pt(i / 10, r * 0.88)
        ticks += f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#888" stroke-width="2"/>'
    nx, ny = pt(frac, r * 0.82)
    return f"""
<div style="text-align:center">
<svg width="{size}" height="{size * 0.72:.0f}" viewBox="0 0 {size} {size * 0.72:.0f}">
  {zones}{ticks}
  <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#333" stroke-width="4" stroke-linecap="round"/>
  <circle cx="{cx}" cy="{cy}" r="{size * 0.03:.1f}" fill="#333"/>
  <text x="{cx}" y="{cy + size * 0.12:.1f}" text-anchor="middle" font-size="{size * 0.09:.0f}" font-weight="700" fill="currentColor">{fmt(value)}</text>
  <text x="{pt(0, r)[0]:.0f}" y="{cy + 16:.0f}" text-anchor="middle" font-size="11" fill="#888">0</text>
  <text x="{pt(1, r)[0]:.0f}" y="{cy + 16:.0f}" text-anchor="middle" font-size="11" fill="#888">{fmt(vmax)}</text>
</svg>
<div style="font-size:0.85rem;color:#888;margin-top:-6px">{label}</div>
</div>"""


def odometer(value: float, label: str, digits: int = 10) -> str:
    s = f"{int(round(value)):0{digits}d}"
    cells = "".join(
        f'<span style="display:inline-block;width:1.4em;padding:4px 0;margin:0 1px;'
        f'background:{"#111" if i < len(s) - 3 else "#B3261E"};color:#fff;border-radius:3px;'
        f'font-family:monospace;font-size:1.5rem;text-align:center;'
        f'box-shadow:inset 0 6px 6px -4px #000,inset 0 -6px 6px -4px #000">{ch}</span>'
        for i, ch in enumerate(s)
    )
    return (f'<div style="text-align:center">{cells}'
            f'<div style="font-size:0.85rem;color:#888;margin-top:4px">{label}</div></div>')


def render_pair(sub: pd.DataFrame, anchor: pd.Timestamp, window_h: int, totals: pd.DataFrame,
                title: str, size: int = 260) -> None:
    """Speedometer = avg tokens/hour over the window ending at anchor; odometer = period total."""
    recent = sub[sub["hr"] > anchor - pd.Timedelta(hours=window_h)]
    rate = recent["tokens"].sum() / window_h
    hourly = (sub[sub["hr"] > anchor - pd.Timedelta(days=30)]
              .groupby("hr")["tokens"].sum())
    p95 = float(hourly.quantile(0.95)) if len(hourly) else 0.0
    vmax = max(p95 * 1.25, rate * 1.1, 1.0)
    st.markdown(f"**{title}**")
    st.markdown(speedometer(rate, vmax, f"tokens / hour (last {window_h}h)", size), unsafe_allow_html=True)
    st.markdown(odometer(totals["tokens"].sum(), "tokens (selected period)"), unsafe_allow_html=True)
    st.caption(f"Credits: {totals['credits'].sum():,.3f}  ·  zones scaled to 30-day p95 hourly rate ({fmt(p95)})")


# ---------- controls ----------
with st.sidebar:
    st.header("Controls")
    window_h = st.segmented_control("Speedometer window", [1, 6, 24], default=6,
                                    format_func=lambda h: f"{h}h") or 6
    period = st.radio("Odometer period", ["Today", "Month to date", "Last 30 days", "All time"], index=1)
    st.button("Refresh data", icon=":material/refresh:", on_click=clear_cache)

with st.spinner("Loading Cortex usage..."):
    data = mask_email_usernames(load_hourly())

if data.empty:
    st.info("No Cortex AI usage found yet.")
    st.stop()

services = sorted(data["service"].unique())
with st.sidebar:
    sel_services = st.multiselect("Services", services, default=services)

data = data[data["service"].isin(sel_services)]
anchor = data["hr"].max() + pd.Timedelta(hours=1) if not data.empty else pd.Timestamp.now(tz="UTC")
now = pd.Timestamp.now(tz="UTC")
start = {
    "Today": now.normalize(),
    "Month to date": now.normalize().replace(day=1),
    "Last 30 days": now - timedelta(days=30),
    "All time": data["hr"].min() if not data.empty else now,
}[period]
in_period = data[data["hr"] >= start]

with st.sidebar:
    st.caption(f"Latest data hour: {(anchor - pd.Timedelta(hours=1)):%Y-%m-%d %H:%M} UTC")

tab_all, tab_user, tab_board = st.tabs(["Overall", "Per user", "Leaderboard"])

# ---------- Overall ----------
with tab_all:
    left, right = st.columns([1, 2])
    with left:
        render_pair(data, anchor, window_h, in_period, "All Cortex AI (combined)", size=320)
    with right:
        st.markdown("**Tokens per day by service**")
        daily = (in_period.assign(day=in_period["hr"].dt.floor("D"))
                 .groupby(["day", "service"])["tokens"].sum().reset_index())
        st.bar_chart(daily, x="day", y="tokens", color="service", height=330)
    st.divider()
    st.subheader("By service")
    cols = st.columns(4)
    for i, svc in enumerate(sel_services):
        with cols[i % 4]:
            render_pair(data[data["service"] == svc], anchor, window_h,
                        in_period[in_period["service"] == svc], svc, size=200)

# ---------- Per user ----------
with tab_user:
    users = sorted(data["user_name"].unique())
    who = st.selectbox("User", ["All users"] + users)
    u_all = data if who == "All users" else data[data["user_name"] == who]
    u_per = in_period if who == "All users" else in_period[in_period["user_name"] == who]
    left, right = st.columns([1, 2])
    with left:
        render_pair(u_all, anchor, window_h, u_per, who, size=320)
    with right:
        st.markdown("**Split by service (selected period)**")
        split = u_per.groupby("service")[["tokens", "credits"]].sum().sort_values("tokens", ascending=False)
        st.dataframe(split, width="stretch",
                     column_config={"tokens": st.column_config.NumberColumn(format="%,d"),
                                    "credits": st.column_config.NumberColumn(format="%.3f")})
        st.markdown("**Hourly trend**")
        trend = u_per.groupby(["hr", "service"])["tokens"].sum().reset_index()
        st.area_chart(trend, x="hr", y="tokens", color="service", height=260)

# ---------- Leaderboard ----------
with tab_board:
    board = (in_period.groupby("user_name")
             .agg(tokens=("tokens", "sum"), credits=("credits", "sum"),
                  services=("service", "nunique"), last_seen=("hr", "max"))
             .sort_values("tokens", ascending=False).reset_index())
    board["share"] = board["tokens"] / max(board["tokens"].sum(), 1)
    st.dataframe(board, width="stretch", hide_index=True,
                 column_config={
                     "tokens": st.column_config.NumberColumn(format="%,d"),
                     "credits": st.column_config.NumberColumn(format="%.3f"),
                     "share": st.column_config.ProgressColumn("share", format="percent", min_value=0, max_value=1),
                 })
