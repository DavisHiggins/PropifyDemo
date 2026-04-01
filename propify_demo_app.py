import hashlib
import math
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Propify (Demo)", page_icon="📈", layout="wide")

# -------------------------
# Helpers
# -------------------------

def stable_rng(*parts: str) -> np.random.Generator:
    seed_str = "|".join(str(p).strip().lower() for p in parts)
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:16], 16) % (2**32)
    return np.random.default_rng(seed)


def demo_model(player: str, stat: str, line: float, opponent: str):
    rng = stable_rng(player, stat, line, opponent)

    stat_base_map = {
        "Points": 23.5,
        "Rebounds": 8.4,
        "Assists": 6.1,
        "PRA": 36.5,
        "Points + Assists": 29.3,
        "Points + Rebounds": 31.1,
    }
    volatility_map = {
        "Points": 6.5,
        "Rebounds": 3.2,
        "Assists": 2.8,
        "PRA": 7.2,
        "Points + Assists": 6.1,
        "Points + Rebounds": 6.0,
    }

    base = stat_base_map.get(stat, 20.0)
    vol = volatility_map.get(stat, 5.0)

    player_bump = ((sum(ord(c) for c in player) % 17) - 8) * 0.33 if player else 0.0
    opp_drag = ((sum(ord(c) for c in opponent) % 11) - 5) * 0.18 if opponent else 0.0
    noise = rng.normal(0, 0.9)

    projection = max(0.5, base + player_bump - opp_drag + noise)
    z = (projection - line) / max(vol, 1.0)
    over_prob = 1 / (1 + math.exp(-1.2 * z))
    over_prob = min(0.94, max(0.06, over_prob))
    under_prob = 1 - over_prob

    trend = np.clip(rng.normal(loc=projection, scale=vol * 0.55, size=10), 0, None)
    trend = np.round(trend, 1)

    x = np.linspace(max(0, projection - 3.5 * vol), projection + 3.5 * vol, 300)
    y = np.exp(-0.5 * ((x - projection) / vol) ** 2)
    y /= np.trapz(y, x)

    confidence_raw = abs(over_prob - 0.5) * 200
    if confidence_raw >= 30:
        confidence = "High"
    elif confidence_raw >= 22:
        confidence = "Medium-High"
    elif confidence_raw >= 14:
        confidence = "Medium"
    else:
        confidence = "Low-Medium"

    return {
        "projection": round(projection, 1),
        "over_prob": round(over_prob * 100, 1),
        "under_prob": round(under_prob * 100, 1),
        "trend": trend,
        "dist_x": x,
        "dist_y": y,
        "confidence": confidence,
        "lean": "OVER" if over_prob > 0.56 else "UNDER" if under_prob > 0.56 else "NEUTRAL",
        "floor": round(max(0, projection - 0.84 * vol), 1),
        "ceiling": round(projection + 0.84 * vol, 1),
        "volatility": round(vol, 1),
    }


def fig_to_png_bytes(fig) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def make_trend_chart(values: np.ndarray, line: float, stat: str) -> bytes:
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    games = np.arange(1, len(values) + 1)
    ax.plot(games, values, linewidth=2.7, marker="o", markersize=4)
    ax.axhline(line, linestyle="--", linewidth=1.8)
    ax.fill_between(games, values, np.min(values) - 2, alpha=0.12)

    ax.spines[:].set_visible(False)
    ax.tick_params(colors="#cbd5e1", labelsize=9)
    ax.grid(alpha=0.18)
    ax.set_title(f"Last 10 Demo Games — {stat}", color="#e2e8f0", fontsize=12, fontweight="bold", loc="left")
    ax.set_xlabel("Game", color="#94a3b8")
    ax.set_ylabel("Output", color="#94a3b8")
    return fig_to_png_bytes(fig)


def make_distribution_chart(x: np.ndarray, y: np.ndarray, line: float, projection: float) -> bytes:
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    ax.plot(x, y, linewidth=2.8)
    ax.fill_between(x, y, alpha=0.14)
    ax.axvline(line, linestyle="--", linewidth=1.8)
    ax.axvline(projection, linestyle=":", linewidth=2.0)

    ax.spines[:].set_visible(False)
    ax.tick_params(colors="#cbd5e1", labelsize=9)
    ax.grid(alpha=0.18)
    ax.set_title("Outcome Distribution (Demo)", color="#e2e8f0", fontsize=12, fontweight="bold", loc="left")
    ax.set_xlabel("Projected Output", color="#94a3b8")
    ax.set_ylabel("Density", color="#94a3b8")
    return fig_to_png_bytes(fig)


# -------------------------
# Styling
# -------------------------
logo_svg = """
<svg width="88" height="88" viewBox="0 0 88 88" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="8" y1="8" x2="80" y2="80" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0F172A"/>
      <stop offset="1" stop-color="#1E293B"/>
    </linearGradient>
    <linearGradient id="bar" x1="18" y1="65" x2="68" y2="20" gradientUnits="userSpaceOnUse">
      <stop stop-color="#10B981"/>
      <stop offset="1" stop-color="#A3E635"/>
    </linearGradient>
  </defs>
  <rect x="7" y="7" width="74" height="74" rx="22" fill="url(#bg)"/>
  <rect x="17" y="50" width="8" height="18" rx="2.5" fill="url(#bar)"/>
  <rect x="29" y="42" width="8" height="26" rx="2.5" fill="url(#bar)"/>
  <rect x="41" y="30" width="8" height="38" rx="2.5" fill="url(#bar)"/>
  <rect x="53" y="21" width="8" height="47" rx="2.5" fill="url(#bar)"/>
  <path d="M18 38C29 40 40 37 49 27C53 23 58 18 69 18" stroke="white" stroke-width="4.5" stroke-linecap="round"/>
  <path d="M62 13H71V22" stroke="white" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

st.markdown(
    f"""
    <style>
        :root {{
            --bg: #0f172a;
            --bg2: #111827;
            --card: rgba(255,255,255,0.82);
            --text: #0f172a;
            --muted: #475569;
            --border: rgba(148,163,184,0.22);
            --green: #10b981;
            --lime: #a3e635;
            --blue: #1d4ed8;
        }}
        .stApp {{
            background: radial-gradient(circle at top left, rgba(16,185,129,0.08), transparent 26%),
                        radial-gradient(circle at top right, rgba(59,130,246,0.08), transparent 26%),
                        linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        }}
        .main .block-container {{
            max-width: 1160px;
            padding-top: 2.2rem;
            padding-bottom: 3rem;
        }}
        .hero {{
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 28px;
            padding: 28px 32px;
            color: white;
            box-shadow: 0 20px 50px rgba(15,23,42,0.22);
        }}
        .hero-grid {{
            display: grid;
            grid-template-columns: 96px 1fr;
            gap: 20px;
            align-items: center;
        }}
        .logo-box {{
            width: 88px;
            height: 88px;
            display:flex;
            align-items:center;
            justify-content:center;
            filter: drop-shadow(0 8px 18px rgba(0,0,0,0.25));
        }}
        .hero-title {{
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1.1;
            margin: 0;
            letter-spacing: -0.02em;
        }}
        .hero-subtitle {{
            margin-top: 8px;
            color: #cbd5e1;
            font-size: 1.05rem;
        }}
        .pill-row {{
            display:flex;
            gap:10px;
            flex-wrap:wrap;
            margin-top:16px;
        }}
        .pill {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.09);
            color: #e2e8f0;
            padding: 8px 12px;
            border-radius: 999px;
            font-size: 0.92rem;
        }}
        .section-card {{
            background: rgba(255,255,255,0.80);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 22px 22px 10px 22px;
            box-shadow: 0 14px 34px rgba(15,23,42,0.08);
        }}
        .notice {{
            background: linear-gradient(135deg, rgba(16,185,129,0.10), rgba(163,230,53,0.12));
            border: 1px solid rgba(16,185,129,0.18);
            border-radius: 18px;
            padding: 14px 16px;
            color: #14532d;
            font-weight: 600;
        }}
        .small-muted {{
            color:#64748b;
            font-size:0.96rem;
        }}
        .metric-card {{
            background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,250,252,0.96));
            border: 1px solid rgba(148,163,184,0.18);
            border-radius: 20px;
            padding: 18px;
            box-shadow: 0 12px 28px rgba(15,23,42,0.06);
        }}
        .metric-label {{
            font-size: 0.88rem;
            color: #64748b;
            margin-bottom: 6px;
            font-weight: 600;
        }}
        .metric-value {{
            font-size: 2.0rem;
            color: #0f172a;
            font-weight: 800;
            letter-spacing: -0.03em;
        }}
        .metric-sub {{
            font-size: 0.88rem;
            color:#475569;
            margin-top: 4px;
        }}
        .lean-box {{
            background: linear-gradient(90deg, #10b981 0%, #84cc16 100%);
            color: white;
            font-weight: 800;
            border-radius: 18px;
            padding: 14px 18px;
            text-align:center;
            letter-spacing: .02em;
            box-shadow: 0 12px 28px rgba(16,185,129,0.22);
        }}
        .demo-footer {{
            color:#475569;
            font-size:0.95rem;
            text-align:center;
            padding: 6px 0 0 0;
        }}
        div[data-testid="stForm"] {{ border: 0 !important; }}
        .stButton > button {{
            width: 100%;
            border-radius: 16px;
            min-height: 3.2rem;
            font-weight: 700;
            border: 0;
            background: linear-gradient(90deg, #10b981 0%, #84cc16 100%);
            color: white;
            box-shadow: 0 10px 22px rgba(16,185,129,0.22);
        }}
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {{
            border-radius: 14px !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Layout
# -------------------------
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-grid">
            <div class="logo-box">{logo_svg}</div>
            <div>
                <div class="hero-title">Propify <span style="font-weight:500; color:#cbd5e1;">(Demo)</span></div>
                <div class="hero-subtitle">Public-facing recruiter demo for a private analytics platform.</div>
                <div class="pill-row">
                    <div class="pill">Single Prop Analyzer</div>
                    <div class="pill">Polished Demo UI</div>
                    <div class="pill">No proprietary model logic exposed</div>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

col_a, col_b = st.columns([1.4, 1], gap="large")

with col_a:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Single Prop Analyzer")
    st.markdown('<div class="small-muted">A polished public demo. Outputs are simulated for portfolio viewing only.</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    with st.form("demo_prop_form"):
        form_col1, form_col2 = st.columns(2)
        with form_col1:
            player = st.text_input("Player Name", placeholder="e.g. LeBron James")
            line = st.number_input("Line", min_value=0.5, max_value=100.0, value=20.5, step=0.5)
        with form_col2:
            stat = st.selectbox("Stat", ["Points", "Rebounds", "Assists", "PRA", "Points + Assists", "Points + Rebounds"])
            opponent = st.text_input("Opponent", placeholder="e.g. BOS")
        submitted = st.form_submit_button("Analyze Prop")

    st.markdown(
        '<div class="notice">This demo exists for portfolio and recruiter review only. The production system, real model logic, tracking engine, authentication, and backend are private.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col_b:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("What this public demo shows")
    st.markdown(
        """
        - A clean product interface
        - Input flow for a single prop analysis
        - Simulated charts and metrics
        - Product design and analytics presentation
        """
    )
    st.markdown("**What is intentionally not included**")
    st.markdown(
        """
        - Proprietary model / weights
        - User accounts or pick tracking
        - Real odds logic
        - Data pipeline and backend services
        """
    )
    st.markdown('</div>', unsafe_allow_html=True)

if submitted:
    if not player.strip() or not opponent.strip():
        st.warning("Enter both a player name and opponent to generate the demo analysis.")
    else:
        result = demo_model(player, stat, float(line), opponent)
        trend_img = make_trend_chart(result["trend"], float(line), stat)
        dist_img = make_distribution_chart(result["dist_x"], result["dist_y"], float(line), result["projection"])

        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Demo Results")

        m1, m2, m3, m4 = st.columns(4, gap="medium")
        metric_data = [
            ("Projection", f"{result['projection']:.1f}", f"Floor {result['floor']:.1f} • Ceiling {result['ceiling']:.1f}"),
            ("Over %", f"{result['over_prob']:.1f}%", f"Confidence: {result['confidence']}"),
            ("Under %", f"{result['under_prob']:.1f}%", f"Volatility: {result['volatility']:.1f}"),
            ("Line", f"{line:.1f}", f"Opponent: {opponent.upper()}"),
        ]
        for col, (label, value, sub) in zip([m1, m2, m3, m4], metric_data):
            with col:
                st.markdown(
                    f'''<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-sub">{sub}</div></div>''',
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="lean-box">Lean: {result["lean"]}</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.image(trend_img)
        with c2:
            st.image(dist_img)

        breakdown = pd.DataFrame(
            {
                "Factor": ["Projection", "Line", "Confidence", "Volatility", "Demo Lean"],
                "Value": [result["projection"], line, result["confidence"], result["volatility"], result["lean"]],
            }
        )
        st.dataframe(breakdown, use_container_width=True, hide_index=True)
        st.markdown('<div class="demo-footer">Note: This output is generated from a simplified deterministic demo model and is not the production engine.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
st.markdown(
    """
    <div class="demo-footer">
        <strong>Propify</strong> is a proprietary analytics platform. This public repository contains a limited demo only.
    </div>
    """,
    unsafe_allow_html=True,
)
