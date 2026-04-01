import hashlib
import math
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

st.set_page_config(page_title="Propify (Demo)", page_icon="📈", layout="wide")

# ─────────────────────────────────────────
# Constants
# ─────────────────────────────────────────
TARHEEL_BLUE = "#7BAFD4"
COLORS = {
    "strong": "#d9f2e3",
    "strong_dark": "#1f7a4d",
    "neutral": "#fff5cf",
    "neutral_dark": "#8a6d1d",
    "risky": "#f9d8d8",
    "risky_dark": "#9b2c2c",
    "info": "#d9ebfa",
    "info_dark": "#1f5f99",
    "surface": "#ffffff",
    "border": "#d9e6f2",
}

STAT_OPTIONS = [
    "Points", "Rebounds", "Assists", "FGM", "FGA", "3PM", "3PA",
    "Steals", "Blocks", "Stocks", "Turnovers", "Fouls", "FTM", "FTA",
    "Fantasy", "PRA", "RA", "PA", "PR",
]

RISK_FLAGS_BY_STAT = {
    "Assists":    ["Assist-based value depends on teammate shot conversion"],
    "PA":         ["Assist-based value depends on teammate shot conversion"],
    "RA":         ["Rebounding value can swing with game script and shot profile"],
    "PRA":        ["Assist-based value depends on teammate shot conversion",
                   "Rebounding value can swing with game script and shot profile"],
    "Steals":     ["Stocks props are highly volatile from game to game"],
    "Blocks":     ["Stocks props are highly volatile from game to game"],
    "Stocks":     ["Stocks props are highly volatile from game to game"],
    "Turnovers":  ["Turnovers depend heavily on ball-handling role and pressure"],
    "Fouls":      ["Fouls are heavily driven by whistle variance and matchup style"],
    "FTM":        ["Free throws made depend on whistle rate and shooting attempts"],
    "FGA":        ["Attempt props depend strongly on role, minutes, and shot volume"],
    "3PA":        ["Attempt props depend strongly on role, minutes, and shot volume"],
    "FGM":        ["Made-shot props depend on both volume and shooting efficiency"],
    "3PM":        ["Made-shot props depend on both volume and shooting efficiency"],
}


# ─────────────────────────────────────────
# Demo model (deterministic from inputs)
# ─────────────────────────────────────────
def stable_rng(*parts):
    seed_str = "|".join(str(p).strip().lower() for p in parts)
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:16], 16) % (2 ** 32)
    return np.random.default_rng(seed)


STAT_BASE = {
    "Points": 23.5, "Rebounds": 8.4, "Assists": 6.1,
    "PRA": 36.5, "PA": 29.3, "PR": 31.1, "RA": 14.5,
    "FGM": 9.1, "FGA": 19.4, "3PM": 2.7, "3PA": 6.3,
    "Steals": 1.3, "Blocks": 0.9, "Stocks": 2.2,
    "Turnovers": 2.8, "Fouls": 2.5, "FTM": 4.1, "FTA": 5.2,
    "Fantasy": 42.0,
}
STAT_VOL = {
    "Points": 6.5, "Rebounds": 3.2, "Assists": 2.8,
    "PRA": 7.2, "PA": 6.1, "PR": 6.0, "RA": 3.9,
    "FGM": 3.1, "FGA": 5.2, "3PM": 1.4, "3PA": 2.6,
    "Steals": 0.9, "Blocks": 0.8, "Stocks": 1.4,
    "Turnovers": 1.3, "Fouls": 1.2, "FTM": 1.8, "FTA": 2.1,
    "Fantasy": 10.2,
}


def demo_model(player: str, stat: str, line: float, opponent: str) -> dict:
    rng = stable_rng(player, stat, str(line), opponent)
    base = STAT_BASE.get(stat, 20.0)
    vol  = STAT_VOL.get(stat, 5.0)

    player_bump = ((sum(ord(c) for c in player) % 17) - 8) * 0.33 if player else 0.0
    opp_drag    = ((sum(ord(c) for c in opponent) % 11) - 5) * 0.18 if opponent else 0.0
    noise       = rng.normal(0, 0.8)

    projection  = max(0.5, round(base + player_bump - opp_drag + noise, 2))
    z           = (projection - line) / max(vol, 1.0)
    over_prob   = 1 / (1 + math.exp(-1.2 * z))
    over_prob   = min(0.93, max(0.07, over_prob))
    under_prob  = 1 - over_prob
    push_prob   = round(rng.uniform(0.01, 0.06), 3)

    floor_proj   = round(max(0, projection - 0.84 * vol), 2)
    ceil_proj    = round(projection + 0.84 * vol, 2)
    median_proj  = round(projection + rng.normal(0, 0.3), 2)

    confidence_raw = abs(over_prob - 0.5) * 200
    if confidence_raw >= 30:
        confidence, conf_num = "High", 5
    elif confidence_raw >= 22:
        confidence, conf_num = "Medium-High", 4
    elif confidence_raw >= 14:
        confidence, conf_num = "Medium", 3
    else:
        confidence, conf_num = "Low-Medium", 2

    lean = "OVER" if over_prob > 0.56 else ("UNDER" if under_prob > 0.56 else "NEUTRAL")

    # Scores
    recent_form_score   = int(rng.integers(42, 91))
    matchup_score       = int(rng.integers(38, 88))
    volatility_score    = int(rng.integers(12, 62))
    minutes_risk_score  = int(rng.integers(8, 48))

    # Hit rates
    def fake_hit_rate(window):
        base_hr = over_prob + rng.normal(0, 0.07)
        return round(min(1.0, max(0.0, base_hr)) * 100, 1)

    # Averages
    season_avg     = round(projection + rng.normal(0.4, 1.1), 2)
    season_median  = round(season_avg - rng.uniform(0.1, 0.8), 2)
    last5_avg      = round(projection + rng.normal(0.2, 1.4), 2)
    last10_avg     = round(projection + rng.normal(0.3, 1.0), 2)
    last15_avg     = round(projection + rng.normal(0.35, 0.9), 2)
    wt_recent_avg  = round(projection + rng.normal(0.15, 0.6), 2)

    proj_minutes   = round(30 + rng.normal(2, 3), 1)
    rest_days      = int(rng.integers(1, 4))
    pace_proxy     = round(112 + rng.normal(0, 4), 1)
    min_mult       = round(1.0 + rng.normal(0, 0.05), 3)
    matchup_mult   = round(1.0 + rng.normal(0, 0.06), 3)
    opp_allow      = round(season_avg + rng.normal(0.5, 1.5), 2)
    role_label     = rng.choice(["Stable Role", "Expanded Role", "Reduced Role"])
    role_alert     = "None"

    # Recent sample table
    n_games = 20
    game_vals = np.clip(rng.normal(loc=projection, scale=vol * 0.85, size=n_games), 0, None)
    game_vals = np.round(game_vals, 1)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_games, freq="3D")[::-1]
    opps  = rng.choice(
        ["LAL","BOS","MIA","GSW","CHI","DAL","PHX","DEN","MIL","ATL","NYK","PHI"],
        size=n_games, replace=True
    )
    home_away_arr = rng.choice(["Home","Away"], size=n_games)
    mins_arr = np.clip(rng.normal(proj_minutes, 3, size=n_games), 15, 42).round(1)

    recent_df = pd.DataFrame({
        "Date":    [d.strftime("%b %d") for d in dates],
        "Opp":     opps,
        "H/A":     home_away_arr,
        "MIN":     mins_arr,
        stat:      game_vals,
        "vs Line": ["✅" if v > line else "❌" for v in game_vals],
    })

    risks = RISK_FLAGS_BY_STAT.get(stat, [])
    if volatility_score >= 40:
        risks = risks + ["High game-to-game volatility"]
    if minutes_risk_score >= 30:
        risks = risks + ["Minutes instability"]
    if rest_days == 0:
        risks = risks + ["Back-to-back fatigue risk"]
    if not risks:
        risks = ["None identified"]

    return {
        "projection": projection,
        "median_projection": median_proj,
        "floor_projection": floor_proj,
        "ceiling_projection": ceil_proj,
        "over_prob": round(over_prob * 100, 1),
        "under_prob": round(under_prob * 100, 1),
        "push_prob": round(push_prob * 100, 1),
        "lean": lean,
        "confidence": confidence,
        "confidence_score_numeric": conf_num,
        "recent_form_score": recent_form_score,
        "matchup_score": matchup_score,
        "volatility_score": volatility_score,
        "minutes_risk_score": minutes_risk_score,
        "season_average": season_avg,
        "season_median": season_median,
        "last5_average": last5_avg,
        "last10_average": last10_avg,
        "last15_average": last15_avg,
        "weighted_recent_average": wt_recent_avg,
        "last5_hit_rate": f"{fake_hit_rate(5)}%",
        "last10_hit_rate": f"{fake_hit_rate(10)}%",
        "last15_hit_rate": f"{fake_hit_rate(15)}%",
        "season_hit_rate": f"{fake_hit_rate(99)}%",
        "projected_minutes": proj_minutes,
        "rest_days": rest_days,
        "home_away": "Neutral",
        "pace_proxy": pace_proxy,
        "minutes_multiplier": min_mult,
        "matchup_multiplier": matchup_mult,
        "opponent_allowance_proxy": opp_allow,
        "role_stability_label": role_label,
        "role_change_alert": role_alert,
        "risks": risks,
        "recent_games_df": recent_df,
        "stat_label": stat.upper(),
    }


# ─────────────────────────────────────────
# Chart helpers
# ─────────────────────────────────────────
def fig_to_png(fig) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def make_trend_chart(values, line: float, stat: str) -> bytes:
    fig, ax = plt.subplots(figsize=(8, 3.2))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f5fafe")

    games = np.arange(1, len(values) + 1)
    ax.plot(games, values, linewidth=2.6, marker="o", markersize=4.2,
            color=TARHEEL_BLUE, label=stat)
    ax.axhline(line, linestyle="--", linewidth=1.8, color="#e74c3c", label=f"Line: {line}")
    ax.fill_between(games, values, np.min(values) - 2, alpha=0.10, color=TARHEEL_BLUE)

    ax.spines[:].set_visible(False)
    ax.tick_params(colors="#475569", labelsize=9)
    ax.grid(alpha=0.18, color="#d9e6f2")
    ax.set_title(f"Recent Sample — {stat}", color="#122235", fontsize=11.5,
                 fontweight="bold", loc="left")
    ax.set_xlabel("Game (most recent → right)", color="#7a8fa0", fontsize=8.5)
    ax.set_ylabel(stat, color="#7a8fa0", fontsize=8.5)
    ax.legend(fontsize=8.5, framealpha=0.5)
    fig.tight_layout()
    return fig_to_png(fig)


def make_distribution_chart(projection: float, vol: float, line: float, stat: str) -> bytes:
    x = np.linspace(max(0, projection - 4 * vol), projection + 4 * vol, 400)
    y = np.exp(-0.5 * ((x - projection) / vol) ** 2)
    y /= np.trapz(y, x)

    fig, ax = plt.subplots(figsize=(8, 3.2))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f5fafe")

    # shade over/under
    ax.fill_between(x, y, where=(x >= line), alpha=0.22, color="#27ae60", label="Over")
    ax.fill_between(x, y, where=(x < line),  alpha=0.18, color="#e74c3c", label="Under")
    ax.plot(x, y, linewidth=2.6, color=TARHEEL_BLUE)
    ax.axvline(line,       linestyle="--", linewidth=1.8, color="#e74c3c",  label=f"Line: {line}")
    ax.axvline(projection, linestyle=":",  linewidth=2.0, color="#17344f", label=f"Projection: {projection}")

    ax.spines[:].set_visible(False)
    ax.tick_params(colors="#475569", labelsize=9)
    ax.grid(alpha=0.18, color="#d9e6f2")
    ax.set_title(f"Outcome Distribution — {stat}", color="#122235", fontsize=11.5,
                 fontweight="bold", loc="left")
    ax.set_xlabel("Projected Output", color="#7a8fa0", fontsize=8.5)
    ax.set_ylabel("Density", color="#7a8fa0", fontsize=8.5)
    ax.legend(fontsize=8.5, framealpha=0.5)
    fig.tight_layout()
    return fig_to_png(fig)


# ─────────────────────────────────────────
# UI Components
# ─────────────────────────────────────────
def inject_css():
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: "Segoe UI", "Trebuchet MS", "Helvetica Neue", Arial, sans-serif;
        }}
        .stApp {{ background: #f5fafe; }}
        .block-container {{ padding-top: 1.3rem; padding-bottom: 2rem; }}

        div[data-testid="stMetric"] {{
            background: white;
            border: 1px solid rgba(0,0,0,0.06);
            padding: 10px 12px;
            border-radius: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        }}

        .primary-card {{
            background: white;
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.05);
            min-height: 110px;
        }}
        .primary-card .label {{
            font-size: 0.92rem; font-weight: 700; opacity: 0.78; color: #122235;
        }}
        .primary-card .value {{
            font-size: 2.25rem; font-weight: 900; margin-top: 6px;
            line-height: 1.05; color: #122235;
        }}

        .secondary-card {{
            background: white;
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 16px;
            padding: 12px 14px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.04);
            min-height: 88px;
        }}
        .secondary-card .label {{
            font-size: 0.88rem; font-weight: 700; opacity: 0.74; color: #122235;
        }}
        .secondary-card .value {{
            font-size: 1.55rem; font-weight: 850; margin-top: 5px;
            line-height: 1.05; color: #122235;
        }}

        .chart-card {{
            background: white;
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 18px;
            padding: 18px 18px 8px 18px;
            box-shadow: 0 4px 14px rgba(0,0,0,0.05);
            margin-top: 14px;
        }}

        .demo-banner {{
            background: linear-gradient(135deg, #fff8e1, #fffde7);
            border: 1.5px solid #f0c040;
            border-radius: 16px;
            padding: 16px 20px;
            margin-bottom: 16px;
        }}

        .fade-in {{
            animation: fadeIn 0.35s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .stDataFrame {{ border-radius: 14px; overflow: hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    st_html(
        f"""
        <div style="
            background: linear-gradient(135deg, #8dc0e2 0%, {TARHEEL_BLUE} 38%, #17344f 100%);
            background-image:
                linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px),
                linear-gradient(135deg, #8dc0e2 0%, {TARHEEL_BLUE} 38%, #17344f 100%);
            background-size: 24px 24px, 24px 24px, 100% 100%;
            padding: 28px 28px;
            border-radius: 24px;
            color: white;
            box-shadow: 0 10px 28px rgba(15,23,42,0.14);
            border: 1px solid rgba(255,255,255,0.18);
            border-top: 6px solid #d7edf9;
            font-family: 'Segoe UI', 'Trebuchet MS', 'Helvetica Neue', Arial, sans-serif;
        ">
            <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:2.42rem;font-weight:900;line-height:1.06;letter-spacing:0.2px;">
                        Propify <span style="font-size:1.3rem;font-weight:600;opacity:0.80;">(Demo)</span>
                    </div>
                    <div style="font-size:1.08rem;opacity:0.96;margin-top:8px;font-weight:600;">
                        Advanced NBA Player Prop Modeling
                    </div>
                    <div style="font-size:0.98rem;opacity:0.90;margin-top:6px;font-style:italic;">
                        Data beats intuition.
                    </div>
                </div>
            </div>
        </div>
        """,
        height=160,
    )


def render_demo_banner():
    st.markdown(
        """
        <div class="demo-banner">
            <div style="font-size:1.02rem;font-weight:800;color:#7a5c00;margin-bottom:6px;">
                🔍 About This Demo
            </div>
            <div style="font-size:0.95rem;color:#5a4400;line-height:1.65;">
                This is a <strong>public-facing demo</strong> of Propify — a private NBA player prop analytics platform.
                The interface, layout, and data structure closely mirror the production system.
                The production version includes a full probabilistic model built on real NBA data, pick tracking with a per-user database,
                multi-leg parlay analysis (2–4 legs), and a complete performance dashboard.
                <br><br>
                This demo generates <strong>simulated outputs</strong> using a deterministic placeholder model — it is
                not connected to any real data source. It exists to demonstrate the product's UI, output structure, and design.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_primary_card(label: str, value: str):
    st.markdown(
        f"""
        <div class="primary-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_secondary_card(label: str, value: str):
    st.markdown(
        f"""
        <div class="secondary-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_style(score, positive_good=True):
    try:
        score = float(score)
    except Exception:
        return "#f3f4f6", "N/A"
    if positive_good:
        if score >= 80: return COLORS["strong"], "Excellent"
        if score >= 65: return "#e8f7ec", "Strong"
        if score >= 45: return COLORS["neutral"], "Neutral"
        if score >= 25: return "#fde7e7", "Weak"
        return "#f7d4d4", "Poor"
    else:
        if score <= 14: return COLORS["strong"], "Excellent"
        if score <= 24: return "#e8f7ec", "Strong"
        if score <= 39: return COLORS["neutral"], "Neutral"
        if score <= 59: return "#fde7e7", "Risky"
        return "#f7d4d4", "Very Risky"


def render_score_card(title: str, value, positive_good: bool = True):
    bg, label = score_style(value, positive_good=positive_good)
    st.markdown(
        f"""
        <div style="
            background:{bg};
            border-radius:16px;
            padding:14px 16px;
            min-height:110px;
            box-shadow:0 3px 12px rgba(0,0,0,0.05);
            border:1px solid rgba(0,0,0,0.06);
        ">
            <div style="font-size:0.88rem;font-weight:700;color:#122235;opacity:0.76;">{title}</div>
            <div style="font-size:2.1rem;font-weight:900;margin-top:6px;color:#122235;">{value}</div>
            <div style="font-size:0.82rem;font-weight:700;margin-top:4px;color:#122235;opacity:0.68;">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hit_rate_section(result: dict):
    st.subheader("Hit Rates vs Line")
    h1, h2, h3, h4 = st.columns(4)
    with h1:
        render_secondary_card("Last 5 Hit Rate", result["last5_hit_rate"])
    with h2:
        render_secondary_card("Last 10 Hit Rate", result["last10_hit_rate"])
    with h3:
        render_secondary_card("Last 15 Hit Rate", result["last15_hit_rate"])
    with h4:
        render_secondary_card("Season Hit Rate", result["season_hit_rate"])
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


def render_footer():
    st.markdown(
        f"""
        <div style="
            text-align:center;
            padding: 28px 0 12px 0;
            color:#8a9db5;
            font-size:0.92rem;
        ">
            <strong style="color:#17344f;">Propify</strong> is a proprietary analytics platform.
            This public repository contains a limited demo only.
            <br>
            <span style="opacity:0.65;">
                © 2026 Davis Higgins. All rights reserved.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────
# Main single prop section
# ─────────────────────────────────────────
def render_single_section():
    st.title("Single Prop Analyzer")

    c1, c2 = st.columns(2)
    with c1:
        player = st.text_input("Player Name", placeholder="e.g. Jayson Tatum", key="single_player")
        stat   = st.selectbox("Stat Type", STAT_OPTIONS, key="single_stat")
        line_opts = [round(x * 0.5, 1) for x in range(1, 101)]
        line = st.selectbox(
            "Line",
            line_opts,
            index=line_opts.index(24.5) if 24.5 in line_opts else 47,
            key="single_line",
            format_func=lambda v: str(int(v)) if float(v).is_integer() else str(v),
        )
    with c2:
        opponent = st.text_input("Opponent Team", placeholder="e.g. Heat", key="single_opponent")
        st.text_area(
            "Optional Notes",
            placeholder="Examples: teammate out, back-to-back, starter tonight...",
            key="single_notes",
        )

    submitted = st.button("Analyze Single Prop", use_container_width=True, key="analyze_btn")

    st.markdown(
        """
        <div style="
            margin-top: 10px;
            padding: 10px 14px;
            background: #fff3cd;
            border: 1px solid #f0c040;
            border-radius: 12px;
            font-size: 0.92rem;
            color: #7a5c00;
            font-weight: 600;
        ">
            ⚠️ <em>All data that is generated below is randomized and purposefully inaccurate. Do not use.</em>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="margin-top:8px;font-size:0.88rem;color:#4a5568;font-style:italic;padding:4px 2px;">
            This data generation closely resembles the layout of some data points displayed in the
            private (soon to be monetized) Propify analytics platform.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if submitted:
        if not player.strip() or not opponent.strip():
            st.warning("Enter both a player name and opponent to generate the demo analysis.")
            return

        result = demo_model(player.strip(), stat, float(line), opponent.strip())
        st.session_state["last_demo_result"] = result
        st.session_state["last_demo_meta"]   = {
            "player": player.strip(), "stat": stat,
            "line": float(line), "opponent": opponent.strip(),
        }

    result   = st.session_state.get("last_demo_result")
    meta     = st.session_state.get("last_demo_meta")

    if not result or not meta:
        return

    st.markdown("<div class='fade-in'>", unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Row 1: primary metrics ──────────────────────────────
    top1, top2, top3, top4, top5 = st.columns(5)
    with top1: render_primary_card("Projection", str(result["projection"]))
    with top2: render_primary_card("Over %",     f"{result['over_prob']:.1f}%")
    with top3: render_primary_card("Under %",    f"{result['under_prob']:.1f}%")
    with top4: render_primary_card("Push %",     f"{result['push_prob']:.1f}%")
    with top5: render_primary_card("Lean",       result["lean"])

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Row 2: secondary metrics ────────────────────────────
    sec1, sec2, sec3, sec4, sec5 = st.columns(5)
    with sec1: render_secondary_card("Median",         str(result["median_projection"]))
    with sec2: render_secondary_card("Floor (20th)",   str(result["floor_projection"]))
    with sec3: render_secondary_card("Ceiling (80th)", str(result["ceiling_projection"]))
    with sec4: render_secondary_card("Confidence",     result["confidence"])
    with sec5: render_secondary_card("Model Version",  "PIE_v2")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Model Scores ────────────────────────────────────────
    st.subheader("Model Scores")
    s1, s2, s3, s4 = st.columns(4)
    with s1: render_score_card("Recent Form Score",  result["recent_form_score"],  True)
    with s2: render_score_card("Matchup Score",      result["matchup_score"],      True)
    with s3: render_score_card("Volatility Score",   result["volatility_score"],   False)
    with s4: render_score_card("Minutes Risk Score", result["minutes_risk_score"], False)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Hit Rates ───────────────────────────────────────────
    render_hit_rate_section(result)

    # ── Context ─────────────────────────────────────────────
    st.subheader("Context")
    cx1, cx2, cx3, cx4 = st.columns(4)
    cx1.metric("Projected Minutes", result["projected_minutes"])
    cx2.metric("Rest Days",         result["rest_days"])
    cx3.metric("Home/Away",         result["home_away"])
    cx4.metric("Pace Proxy",        result["pace_proxy"])

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Key Statistics ──────────────────────────────────────
    st.subheader("Key Statistics")
    reasons = [
        f"Season average: {result['season_average']:.2f}",
        f"Season median: {result['season_median']:.2f}",
        f"Weighted recent avg: {result['weighted_recent_average']:.2f}",
        f"Last 5 average: {result['last5_average']:.2f}",
        f"Last 10 average: {result['last10_average']:.2f}",
        f"Last 15 average: {result['last15_average']:.2f}",
        f"Projected minutes: {result['projected_minutes']}",
        f"Minutes multiplier: {result['minutes_multiplier']}",
        f"Matchup multiplier: {result['matchup_multiplier']}",
        f"Opp allowance proxy: {result['opponent_allowance_proxy']}",
        f"Season hit rate: {result['season_hit_rate']}",
        f"Last 10 hit rate: {result['last10_hit_rate']}",
        f"Last 5 hit rate: {result['last5_hit_rate']}",
        f"Role: {result['role_stability_label']}",
    ]
    kcols = st.columns(4)
    for i, item in enumerate(reasons):
        with kcols[i % 4]:
            st.write(f"• {item}")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Risk Flags ──────────────────────────────────────────
    st.subheader("Risk Flags")
    rcols = st.columns(4)
    for i, item in enumerate(result["risks"]):
        with rcols[i % 4]:
            st.write(f"• {item}")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Charts ──────────────────────────────────────────────
    vol = STAT_VOL.get(meta["stat"], 5.0)
    recent_vals = result["recent_games_df"][meta["stat"]].values[:10][::-1]

    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        trend_img = make_trend_chart(recent_vals, float(meta["line"]), meta["stat"])
        st.image(trend_img, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with ch2:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        dist_img = make_distribution_chart(result["projection"], vol, float(meta["line"]), meta["stat"])
        st.image(dist_img, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Recent Sample ───────────────────────────────────────
    st.subheader("Recent Sample")
    sample_df = result["recent_games_df"].copy()

    sc_left, sc_right = st.columns([5, 1])
    with sc_right:
        window = st.selectbox(
            "Window",
            ["Last 10", "Last 20", "Season"],
            index=0,
            key="demo_window",
        )
    if window == "Last 10":
        display_df = sample_df.head(10)
    elif window == "Last 20":
        display_df = sample_df.head(20)
    else:
        display_df = sample_df

    st.dataframe(display_df.reset_index(drop=True), use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────
# App entry
# ─────────────────────────────────────────
inject_css()
render_header()

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
render_demo_banner()

tab_single, tab_about = st.tabs(["Single Prop Analyzer", "About Propify"])

with tab_single:
    render_single_section()

with tab_about:
    st.markdown(
        """
        ## About Propify

        Propify is a privately developed NBA player prop analytics platform designed to identify
        statistically favorable betting opportunities through probabilistic modeling and contextual game analysis.

        **What the production system includes:**
        - A custom probabilistic projection engine using real NBA data via nba_api
        - Over/under probability outputs derived from normal distribution modeling
        - Confidence scoring across five tiers (Low → High)
        - Matchup-based adjustments using opponent allowance data
        - Volatility and minutes-risk metrics
        - Recent-form weighting with trimmed mean calculations
        - 2–4 leg parlay builder with compounded probability outputs
        - Full per-user pick tracking and performance dashboard (Supabase backend)
        - Row-level security ensuring no shared data between accounts

        **What this demo does not include:**
        - Any real NBA data or live API connections
        - The proprietary model logic, weights, or feature engineering
        - User authentication or pick tracking
        - Parlay analysis sections
        - Backend infrastructure

        This demo is intentionally limited to the Single Prop Analyzer tab with
        simulated outputs. The production codebase is private.
        """,
    )

render_footer()
