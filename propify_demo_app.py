import hashlib
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

st.set_page_config(page_title="Propify Demo", page_icon="📈", layout="wide")

TARHEEL_BLUE = "#7BAFD4"
APP_DIR = Path(__file__).parent
PROPIFY_LOGO_PATH = APP_DIR / "proptrans.png"
DH_LOGO_PATH = APP_DIR / "dhtrans(3).png"
NAVY = "#10213a"
LIGHT_TEXT = "#f5f7fb"
MUTED = "#c9d3de"
CARD_BG = "#f3f4f6"
BORDER = "rgba(138,157,181,0.30)"

STAT_OPTIONS = [
    "Points", "Rebounds", "Assists", "FGM", "FGA", "3PM", "3PA",
    "Steals", "Blocks", "Stocks", "Turnovers", "Fouls", "FTM", "FTA",
    "Fantasy", "PRA", "RA", "PA", "PR",
]
TEAM_OPTIONS = [
    "Hawks","Celtics","Nets","Hornets","Bulls","Cavaliers","Mavericks","Nuggets","Pistons",
    "Warriors","Rockets","Pacers","Clippers","Lakers","Grizzlies","Heat","Bucks","Timberwolves",
    "Pelicans","Knicks","Thunder","Magic","76ers","Suns","Trail Blazers","Kings","Spurs","Raptors","Jazz","Wizards"
]
PLAYER_OPTIONS = [
    "Shai Gilgeous-Alexander","Nikola Jokic","Luka Doncic","Jayson Tatum","Anthony Davis","LeBron James",
    "Stephen Curry","Trae Young","Paolo Banchero","Devin Booker","Jalen Brunson","Donovan Mitchell",
    "AJ Green","Bilal Coulibaly","Paul George","Tyrese Haliburton","Bam Adebayo","Jaren Jackson Jr.",
    "Coby White","Kawhi Leonard","Rudy Gobert","A.J. Lawson","Jalen Williams","Kevin Durant"
]

# ---------- Demo model ----------
def stable_rng(*parts):
    seed_str = "|".join(str(p).strip().lower() for p in parts)
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest()[:16], 16) % (2 ** 32)
    return np.random.default_rng(seed)

STAT_BASE = {
    "Points": 22.0, "Rebounds": 8.2, "Assists": 5.9, "PRA": 35.0, "PA": 28.8, "PR": 30.2, "RA": 14.1,
    "FGM": 8.3, "FGA": 18.5, "3PM": 2.6, "3PA": 6.8, "Steals": 1.4, "Blocks": 1.0, "Stocks": 2.5,
    "Turnovers": 2.9, "Fouls": 2.3, "FTM": 4.6, "FTA": 5.8, "Fantasy": 40.0,
}
STAT_VOL = {
    "Points": 6.2, "Rebounds": 3.0, "Assists": 2.7, "PRA": 7.4, "PA": 6.0, "PR": 5.8, "RA": 4.0,
    "FGM": 2.7, "FGA": 5.2, "3PM": 1.5, "3PA": 2.7, "Steals": 0.8, "Blocks": 0.8, "Stocks": 1.3,
    "Turnovers": 1.2, "Fouls": 1.1, "FTM": 1.7, "FTA": 2.0, "Fantasy": 10.0,
}

def demo_model(player: str, stat: str, line: float, opponent: str) -> dict:
    rng = stable_rng(player, stat, line, opponent)
    base = STAT_BASE.get(stat, 20.0)
    vol = STAT_VOL.get(stat, 5.0)
    player_bump = ((sum(ord(c) for c in player) % 19) - 9) * 0.28 if player else 0.0
    opp_drag = ((sum(ord(c) for c in opponent) % 11) - 5) * 0.20 if opponent else 0.0
    projection = round(max(0.5, base + player_bump - opp_drag + rng.normal(0, 0.75)), 2)
    z = (projection - line) / max(vol, 1.0)
    over_prob = 1 / (1 + math.exp(-1.15 * z))
    over_prob = min(0.93, max(0.07, over_prob))
    under_prob = 1 - over_prob
    push_prob = round(float(rng.uniform(0.01, 0.05)), 3)
    lean = "OVER" if over_prob >= under_prob else "UNDER"

    conf_raw = abs(over_prob - 0.5) * 200
    if conf_raw >= 30:
        confidence = "High"
    elif conf_raw >= 22:
        confidence = "Medium-High"
    elif conf_raw >= 14:
        confidence = "Medium"
    else:
        confidence = "Low-Medium"

    recent_form = int(rng.integers(48, 91))
    matchup_score = int(rng.integers(40, 85))
    volatility = int(rng.integers(14, 63))
    minutes_risk = int(rng.integers(8, 49))

    season_avg = round(projection + rng.normal(0.2, 1.0), 2)
    last10_avg = round(projection + rng.normal(0.15, 1.1), 2)
    fair_line = round(projection + rng.normal(0.0, 0.35), 1)
    season_hit = round((over_prob if lean == "OVER" else under_prob) * 100 + rng.normal(0, 5), 1)
    season_hit = max(8.0, min(91.0, season_hit))
    ml_proj = round(projection + rng.normal(-0.6, 0.9), 2)
    rules_proj = round(projection + rng.normal(0.3, 0.6), 2)
    ml_blend = int(rng.integers(24, 48))
    edge = round(projection - line, 2)
    if lean == "UNDER":
        edge = -abs(edge)
    else:
        edge = abs(edge)

    rows = []
    for i in range(10):
        date = pd.Timestamp("2026-04-12") - pd.Timedelta(days=i * int(rng.integers(2, 5)))
        stat_val = max(0, round(projection + rng.normal(0, vol * 0.7)))
        outcome = "over" if stat_val > line else ("push" if stat_val == line else "under")
        rows.append({
            "Game Date": date.strftime("%m/%d/%Y"),
            "Matchup": f"{player.split()[-1][:3].upper()} vs. {opponent[:3].upper()}",
            "W/L": "W" if i % 2 == 0 else "L",
            "MIN": int(max(18, rng.normal(31, 4))),
            "PTS": int(max(0, stat_val if stat == "Points" else rng.normal(16, 7))),
            "REB": int(max(0, rng.normal(7, 3))),
            "AST": int(max(0, rng.normal(5, 2.5))),
            "Pick Result": outcome,
        })
    df = pd.DataFrame(rows)

    return {
        "projection": projection,
        "over_prob": over_prob * 100,
        "under_prob": under_prob * 100,
        "push_prob": push_prob * 100,
        "edge": edge,
        "season_hit": season_hit,
        "fair_line": fair_line,
        "fair_odds_over": f"+{int(abs((1/(max(over_prob, 1e-6)))*100 - 100))}",
        "fair_odds_under": f"-{int(abs((1/(max(under_prob, 1e-6)))*100 - 100))}",
        "confidence": confidence,
        "ev_pct": "N/A",
        "recent_form": recent_form,
        "matchup_score": matchup_score,
        "volatility_score": volatility,
        "minutes_risk_score": minutes_risk,
        "season_avg": season_avg,
        "last10_avg": last10_avg,
        "rules_proj": rules_proj,
        "ml_proj": ml_proj,
        "ml_blend": ml_blend,
        "lean": lean,
        "recent_df": df,
    }

# ---------- State ----------
if "app_view" not in st.session_state:
    st.session_state.app_view = "home"
if "demo_last_result" not in st.session_state:
    st.session_state.demo_last_result = None
if "demo_last_inputs" not in st.session_state:
    st.session_state.demo_last_inputs = {}
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = "Deep Mode"

# ---------- CSS ----------
st.markdown(f"""
<style>
    .stApp {{
        background: {NAVY};
    }}
    .block-container {{
        padding-top: 0.6rem;
        padding-bottom: 2rem;
        max-width: 96rem;
    }}
    .demo-topbar {{
        display:flex; align-items:center; justify-content:flex-start;
        min-height:34px; margin:-0.15rem 0 1.9rem 0; padding-top:0;
    }}
    .demo-topbar img {{
        width:34px; height:34px; object-fit:contain; flex-shrink:0; margin:0;
    }}
    .demo-topbar-engine {{
        margin-left:0.55rem; font-size:1.32rem; font-weight:700; color:{TARHEEL_BLUE};
        line-height:1; display:flex; align-items:center; height:34px;
    }}
    .demo-header-note {{
        color:{MUTED}; font-size:0.88rem; line-height:1.5; text-align:right; margin-top:0.15rem;
    }}
    .demo-pill {{
        display:inline-block; padding:0.38rem 0.78rem; border-radius:999px;
        border:1px solid rgba(255,255,255,0.16); color:{LIGHT_TEXT}; font-size:0.82rem;
        background:rgba(255,255,255,0.04); margin-left:0.4rem;
    }}
    .propify-section-title {{
        margin:0.1rem 0 1rem 0;
    }}
    .propify-section-title h1 {{
        margin:0; font-size:3rem; font-weight:800; line-height:1.05; color:{LIGHT_TEXT};
    }}
    .propify-section-divider {{
        width:120px; height:4px; border-radius:999px; background:linear-gradient(90deg, {TARHEEL_BLUE} 0%, #9ec7e6 100%);
        margin-top:0.18rem;
    }}
    .demo-banner {{
        background:linear-gradient(180deg, rgba(123,175,212,0.16), rgba(123,175,212,0.08));
        border:1px solid rgba(123,175,212,0.28);
        border-radius:18px;
        padding:1rem 1.1rem;
        margin:0 0 1.1rem 0;
        color:{LIGHT_TEXT};
    }}
    .demo-note {{
        color:{MUTED}; font-size:0.92rem; line-height:1.7;
    }}
    .blur-card {{
        background:{CARD_BG};
        border-radius:22px;
        padding:1.05rem 1.1rem;
        min-height:115px;
    }}
    .blur-card .label {{
        font-size:0.9rem; font-weight:700; color:#4b5563; opacity:0.95;
    }}
    .blur-card .blur-value {{
        margin-top:0.6rem;
        font-size:2.05rem; font-weight:900; color:#122235;
        filter: blur(8px);
        user-select:none;
    }}
    .blur-card .blur-small {{
        margin-top:0.65rem; font-size:1.18rem; font-weight:700; color:#122235; filter: blur(7px);
    }}
    .blur-block {{
        filter: blur(10px);
        user-select:none;
        pointer-events:none;
    }}
    .blur-box {{
        background:{CARD_BG};
        border-radius:18px;
        min-height:160px;
        padding:1rem;
    }}
    .locked-area {{
        position:relative;
    }}
    .locked-overlay {{
        position:absolute; inset:0;
        backdrop-filter: blur(7px);
        background: rgba(16,33,58,0.28);
        border-radius:18px;
        display:flex; align-items:center; justify-content:center;
        text-align:center; padding:1.4rem; z-index:5;
    }}
    .locked-overlay-inner {{
        max-width:580px; background:rgba(16,33,58,0.92); color:{LIGHT_TEXT}; border:1px solid rgba(123,175,212,0.28);
        border-radius:18px; padding:1.15rem 1.2rem;
        box-shadow:0 16px 30px rgba(0,0,0,0.20);
    }}
    .locked-title {{
        font-size:1.06rem; font-weight:800; color:{TARHEEL_BLUE}; margin-bottom:0.4rem;
    }}
    .locked-copy {{
        font-size:0.95rem; line-height:1.6; color:{LIGHT_TEXT};
    }}
    .demo-subtext {{
        font-size:0.82rem; color:{MUTED}; margin:0 0 0.45rem 0;
    }}
    .demo-blue-line {{
        color:{TARHEEL_BLUE}; font-size:0.82rem; margin:-0.08rem 0 0.7rem 0;
    }}
    .risk-box {{
        background:#17344f; border-left:4px solid {TARHEEL_BLUE}; border-radius:12px; padding:0.85rem 1rem; margin:0.25rem 0 0.8rem 0;
    }}
    .risk-title {{ font-size:0.76rem; opacity:0.78; color:{LIGHT_TEXT}; }}
    .risk-body {{ font-size:1.02rem; font-weight:700; color:{LIGHT_TEXT}; filter: blur(6px); }}
    .demo-table-wrap {{
        background:{CARD_BG}; border-radius:18px; padding:0.9rem; overflow-x:auto;
        border:1px solid rgba(18,34,53,0.10);
    }}
    .demo-table {{
        width:100%; border-collapse:collapse; color:#122235; font-size:0.92rem;
    }}
    .demo-table th {{
        padding:0.75rem 0.65rem; background:#eff4f8; text-align:center; font-weight:800; color:#122235; filter: blur(6px);
    }}
    .demo-table td {{
        padding:0.7rem 0.6rem; text-align:center; border-top:1px solid #d6dee8; filter: blur(7px);
    }}
    .demo-table-caption {{
        color:#122235; font-size:0.92rem; margin-bottom:0.6rem; filter: blur(6px);
    }}
    .hero-credit {{
        text-align:center; margin-top:0.45rem; color:{MUTED}; font-size:0.92rem;
    }}
    .hero-credit em {{ color:{LIGHT_TEXT}; }}
    .disabled-analyze {{
        position:relative;
    }}
    .disabled-analyze button {{
        filter: blur(2px) grayscale(0.2);
        pointer-events:none;
    }}
    .feature-card-title {{
        color:{LIGHT_TEXT}; font-size:1.08rem; font-weight:700; margin:0 0 0.85rem 0;
    }}
    .small-heading {{
        color:{LIGHT_TEXT}; font-size:2.05rem; font-weight:800; line-height:1.15; margin:0 0 0.5rem 0;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap:2.4rem;
        justify-content:flex-start;
        align-items:center;
        padding-left:0 !important;
        margin-left:-0.45rem;
        border-bottom:1.5px solid rgba(255,255,255,0.62);
        margin-top:0.95rem;
        margin-bottom:1.1rem;
        width:max-content !important;
        max-width:max-content !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        height:2.8rem;
        margin-right:0.35rem;
        white-space:nowrap;
        border-radius:10px 10px 0 0;
        padding-left:0.15rem;
        padding-right:0.15rem;
        font-weight:700;
        font-size:1.08rem;
        color:{LIGHT_TEXT} !important;
        border-bottom:2px solid transparent !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        background: {TARHEEL_BLUE} !important;
        height:3px !important;
        border-radius:999px !important;
    }}
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stNumberInput"] input,
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] input {{
        color:{LIGHT_TEXT} !important;
        -webkit-text-fill-color:{LIGHT_TEXT} !important;
    }}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def render_header():
    left, right = st.columns([8.4, 1.6])
    with left:
        st.markdown(
            """
            <div class="demo-topbar">
                <img src="data:image/png;base64,PLACEHOLDER_ICON" alt="Propify" />
                <div class="demo-topbar-engine">Propify AI Engine Demo</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""<div class="demo-header-note">
                <span class="demo-pill">Public Demo</span>
                <span class="demo-pill">Private analytics blurred</span>
            </div>""",
            unsafe_allow_html=True,
        )

def render_section_title(title: str):
    st.markdown(
        f"""
        <div class="propify-section-title">
            <h1>{title}</h1>
            <div class="propify-section-divider"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_thin_line():
    st.markdown(
        "<div style='height:2px; width:100%; background:rgba(255,255,255,0.22); margin:0.08rem 0 1.15rem 0; border-radius:999px;'></div>",
        unsafe_allow_html=True,
    )

def render_blur_card(label: str, value: str = "88.8%", small: bool = False):
    cls = "blur-small" if small else "blur-value"
    st.markdown(
        f"""
        <div class="blur-card">
            <div class="label">{label}</div>
            <div class="{cls}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_demo_card(label: str, value: str = "88.8%", small: bool = False, blur_label: bool = False, blur_value: bool = True):
    cls = "blur-small" if small else "blur-value"
    label_class = "label blur-label" if blur_label else "label"
    value_class = cls if blur_value else ""
    st.markdown(
        f"""
        <div class="blur-card">
            <div class="{label_class}">{label}</div>
            <div class="{value_class}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def blur_preview_message(title="Demo Preview", copy="Values are intentionally obscured in the public demo. Full Propify access will open publicly sometime in 2026."):
    st.markdown(
        f"""
        <div class="locked-overlay">
            <div class="locked-overlay-inner">
                <div class="locked-title">{title}</div>
                <div class="locked-copy">{copy}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_demo_home():
    st.markdown("<div class='demo-home-wrap'>", unsafe_allow_html=True)
    st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)
    left, center, right = st.columns([1.2, 1.6, 1.2])
    with center:
        if PROPIFY_LOGO_PATH.exists():
            st.image(str(PROPIFY_LOGO_PATH), width=520)
        st.markdown(
            """
            <div class="hero-credit">
                <strong style="color:#7BAFD4;">Propify Demo</strong> — public UI preview of the private platform.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)
        cols = st.columns([1.0, 2.0, 1.0])
        with cols[1]:
            if st.button("Enter Propify Demo", use_container_width=True):
                st.session_state.app_view = "main"
                st.rerun()
        st.markdown("<div style='height:0.85rem;'></div>", unsafe_allow_html=True)
        c2 = st.columns([1.45, 0.3, 1.45])
        with c2[1]:
            if DH_LOGO_PATH.exists():
                st.image(str(DH_LOGO_PATH), width=95)
    st.markdown("</div>", unsafe_allow_html=True)

def render_play_summary(result, player, stat, line):
    st.markdown(f"<div class='demo-subtext blur-block'>Engine Projections | Rules: {result['rules_proj']:.2f} + ML: {result['ml_proj']:.2f} | {result['ml_blend']}% ML</div>", unsafe_allow_html=True)
    st.markdown("<div class='small-heading'>Play Summary</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='demo-blue-line'>{player} {result['lean'].lower()} {line:g} {stat.lower()}</div>", unsafe_allow_html=True)
    cols = st.columns(6)
    blur_map = {
        "Best Side": False,
        "Final Projection": False,
        "Edge vs Line": False,
        "Confidence Tier": False,
        "Minutes Risk": True,
        "ML Changed Result": True,
    }
    labels = ["Best Side", "Final Projection", "Edge vs Line", "Confidence Tier", "Minutes Risk", "ML Changed Result"]
    for col, label in zip(cols, labels):
        with col:
            render_demo_card(label, "blurred", small=True, blur_label=blur_map[label], blur_value=True)
    st.markdown(
        """
        <div class="risk-box">
            <div class="risk-title blur-block">Most Important Risk</div>
            <div class="risk-body">Minutes uncertainty</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_blurred_primary_grid():
    row1 = st.columns(5)
    blur_top = {"Projection": False, "Over %": False, "Under %": False, "Edge vs Line": True, "Season Hit Rate": True}
    for col, label in zip(row1, ["Projection", "Over %", "Under %", "Edge vs Line", "Season Hit Rate"]):
        with col:
            render_demo_card(label, blur_label=blur_top[label])
    row2 = st.columns(5)
    blur_bottom = {"Fair Line": False, "Fair Odds O": False, "Fair Odds U": False, "Confidence": True, "EV %": False}
    for col, label in zip(row2, ["Fair Line", "Fair Odds O", "Fair Odds U", "Confidence", "EV %"]):
        with col:
            render_demo_card(label, small=True, blur_label=blur_bottom[label])

def render_blurred_expander():
    with st.expander("Projection Method Details", expanded=False):
        row1 = st.columns(4)
        blur_row1 = {"Final Projection": True, "Rules Projection": True, "ML Projection": True, "ML Blend %": True}
        for col, label in zip(row1, ["Final Projection", "Rules Projection", "ML Projection", "ML Blend %"]):
            with col:
                render_demo_card(label, small=True, blur_label=blur_row1[label])
        row2 = st.columns(4)
        blur_row2 = {"Train Rows": True, "Train R²": True, "Residual Std": True, "Validation MAE": True}
        for col, label in zip(row2, ["Train Rows", "Train R²", "Residual Std", "Validation MAE"]):
            with col:
                render_demo_card(label, small=True, blur_label=blur_row2[label])
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        render_demo_card("Method", small=True, blur_label=False)

def render_demo_scores_tab():
    st.markdown("<div class='feature-card-title'>Model Scores</div>", unsafe_allow_html=True)
    row = st.columns(4)
    for col, title in zip(row, ["Recent Form Score", "Matchup Score", "Volatility Score", "Minutes Risk Score"]):
        with col:
            render_demo_card(title, small=True, blur_label=True)
    render_thin_line()
    st.markdown("<div class='feature-card-title'>Hit Rate</div>", unsafe_allow_html=True)
    row2 = st.columns(4)
    for col, title in zip(row2, ["Last 5", "Last 10", "Last 15", "Season"]):
        with col:
            render_demo_card(title, small=True, blur_label=True)

def render_demo_context_tab():
    st.markdown("<div class='feature-card-title'>Context</div>", unsafe_allow_html=True)
    row = st.columns(4)
    for col, title in zip(row, ["Projected Minutes", "Rest Days", "Home/Away", "Pace Proxy"]):
        with col:
            render_demo_card(title, small=True, blur_label=True)
    render_thin_line()
    st.markdown("<div class='feature-card-title'>Comparable Picks</div>", unsafe_allow_html=True)
    st.markdown('<div class="blur-box blur-block"></div>', unsafe_allow_html=True)

def render_demo_stats_table(result):
    st.markdown("<div class='feature-card-title'>Stats Table</div>", unsafe_allow_html=True)
    controls = st.columns([1.12, 1.02, 1.18, 1.08])
    with controls[0]:
        st.toggle("Season Avg Line", value=True, disabled=True)
    with controls[1]:
        st.toggle("Prop Line", value=True, disabled=True)
    with controls[2]:
        st.toggle("Opponent-Specific", value=False, disabled=True)
    with controls[3]:
        st.selectbox("Window", ["Season", "Last 10", "All-Time"], index=0, disabled=True)
    df = result["recent_df"][["Game Date","Matchup","W/L","MIN","PTS","REB","AST","Pick Result"]]
    html = ['<div class="demo-table-wrap"><div class="demo-table-caption blur-block">Season Avg: 18.4 | Prop Line: 20.5</div><table class="demo-table blur-block"><thead><tr>']
    for c in df.columns:
        html.append(f"<th>{c}</th>")
    html.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        html.append("<tr>" + "".join(f"<td>{row[c]}</td>" for c in df.columns) + "</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

def render_analyze_tab():
    render_section_title("Single Prop Analyzer")
    st.markdown(
        """
        <div class="demo-banner">
            <div style="font-size:1.02rem;font-weight:800;color:#d8ecfb;margin-bottom:6px;">Demo Notes</div>
            <div class="demo-note">
                The Single Prop Analyzer—Propify’s core engine—combines machine learning, statistical modeling, and real-time context to deliver precise projections and probabilities. Built through extensive iteration and refinement, it is engineered for accuracy and reliability. Analyze a prop below to preview the interface and calculations; demo outputs are placeholder-based and blurred to protect proprietary logic. 
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top = st.columns([7, 1, 1])
    with top[1]:
        if st.button("Clear", use_container_width=True):
            st.session_state.demo_last_result = None
            st.session_state.demo_last_inputs = {}
            st.rerun()
    with top[2]:
        st.button("History", use_container_width=True, disabled=True)

    c1, c2 = st.columns(2)
    with c1:
        player = st.selectbox("Player Name", PLAYER_OPTIONS, index=0)
        stat = st.selectbox("Stat Type", STAT_OPTIONS, index=0)
        line = st.number_input("Line", min_value=0.0, step=0.5, value=24.5)
        opponent = st.selectbox("Opponent Team", TEAM_OPTIONS, index=0)
    with c2:
        st.number_input("Multiplier (optional)", min_value=0.0, step=0.1, value=0.0)
        st.text_area("Optional Notes", placeholder="Examples: teammate out, back-to-back, starter tonight.")
    st.markdown("<div style='height:1.35rem;'></div>", unsafe_allow_html=True)
    if st.button("Analyze Single Prop", use_container_width=True):
        st.session_state.demo_last_result = demo_model(player, stat, float(line), opponent)
        st.session_state.demo_last_inputs = {"player": player, "stat": stat, "line": float(line), "opponent": opponent}
        st.rerun()
    st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

    result = st.session_state.demo_last_result
    inputs = st.session_state.demo_last_inputs
    if not result:
        st.info("Run a demo analysis to preview the full single-prop layout.")
        return

    render_play_summary(result, inputs["player"], inputs["stat"], inputs["line"])
    render_blurred_primary_grid()
    render_blurred_expander()
    subtabs = st.tabs(["Projection & Scores", "Context & Risk", "Recent Sample"])
    with subtabs[0]:
        render_demo_scores_tab()
    with subtabs[1]:
        render_demo_context_tab()
    with subtabs[2]:
        render_demo_stats_table(result)

def render_locked_parlay_tab(legs: int):
    render_section_title(f"{legs}-Leg Parlay")
    cols = st.columns(legs)
    for i in range(legs):
        with cols[i]:
            st.markdown(f"<div class='feature-card-title'>Leg {i+1}</div>", unsafe_allow_html=True)
            st.selectbox("Player Name", PLAYER_OPTIONS, index=min(i, len(PLAYER_OPTIONS)-1), key=f"p_{legs}_{i}")
            st.selectbox("Stat Type", STAT_OPTIONS, index=0, key=f"s_{legs}_{i}")
            st.selectbox("Side", ["OVER", "UNDER"], index=0, key=f"side_{legs}_{i}")
            st.number_input("Line", min_value=0.0, step=0.5, value=10.5, key=f"line_{legs}_{i}")
            st.selectbox("Opponent Team", TEAM_OPTIONS, index=i % len(TEAM_OPTIONS), key=f"opp_{legs}_{i}")
    extra = st.columns(2)
    with extra[0]:
        st.number_input("Multiplier (optional)", min_value=0.0, step=0.1, value=0.0, key=f"mult_{legs}")
    with extra[1]:
        st.text_input("Notes", key=f"notes_{legs}")
    st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="disabled-analyze">', unsafe_allow_html=True)
    st.button(f"Analyze {legs}-Leg Parlay", use_container_width=True, disabled=True, key=f"an_{legs}")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="locked-area"><div class="blur-box blur-block"></div>', unsafe_allow_html=True)
    blur_preview_message("Private multi-leg output", "Parlay probabilities, leg summaries, sticky context, saved entries, and private grading features are intentionally hidden in the public demo.")
    st.markdown("</div>", unsafe_allow_html=True)

def render_tracking_tab():
    render_section_title("Pick Tracker")
    st.markdown(
        """
        <div class="locked-overlay-inner" style="margin-bottom:1rem;">
            <div class="locked-title">Tracking preview only</div>
            <div class="locked-copy">Per-user pick tracking widgets are shown here as part of the private product structure and workflow preview.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    row = st.columns(4)
    for c, label in zip(row, ["Record", "Win Rate", "Net Profit", "ROI"]):
        with c:
            render_blur_card(label, small=True)
    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="locked-area"><div class="blur-box blur-block" style="min-height:320px;"></div>', unsafe_allow_html=True)
    blur_preview_message("Tracker dashboard preview", "Charts, pick editing, grading controls, ROI dashboards, and account-linked history are hidden.")
    st.markdown("</div>", unsafe_allow_html=True)

def render_learn_tab():
    learn_about, learn_metrics, learn_faq = st.tabs(["How to Use Propify", "Metric Guide", "FAQs"])
    with learn_about:
        render_section_title("How to Use Propify")
        st.markdown('<div class="locked-area"><div class="blur-box blur-block" style="min-height:260px;"></div>', unsafe_allow_html=True)
        blur_preview_message("Knowledge-base preview", "This section previews the product education layout while keeping the internal guidance and proprietary explanations obscured.")
        st.markdown("</div>", unsafe_allow_html=True)
    with learn_metrics:
        render_section_title("Metric Guide")
        st.markdown('<div class="locked-area"><div class="blur-box blur-block" style="min-height:360px;"></div>', unsafe_allow_html=True)
        blur_preview_message("Metric guide preview", "This section previews how metric definitions, risk explanations, and model guidance are organized in the full product.")
        st.markdown("</div>", unsafe_allow_html=True)
    with learn_faq:
        render_section_title("FAQs")
        st.markdown('<div class="locked-area"><div class="blur-box blur-block" style="min-height:240px;"></div>', unsafe_allow_html=True)
        blur_preview_message("FAQ preview", "This section previews the support and FAQ layout used in the full product.")
        st.markdown("</div>", unsafe_allow_html=True)

def render_account_tab():
    render_section_title("Account")
    st.markdown('<div class="locked-area"><div class="blur-box blur-block" style="min-height:220px;"></div>', unsafe_allow_html=True)
    blur_preview_message("Account preview", "This section previews account-oriented product areas while keeping private account features obscured.")
    st.markdown("</div>", unsafe_allow_html=True)

def main():
    # replace placeholder icon in header template using logo file
    if st.session_state.app_view == "home":
        render_demo_home()
        return

    # header icon uses logo file as base64
    render_header()
    st.markdown(
        """
        <div class="demo-banner" style="margin-top:-0.6rem;">
            <div style="font-size:1.02rem;font-weight:800;color:#d8ecfb;margin-bottom:6px;">Public Demo Preview</div>
            <div class="demo-note">
                This build mirrors the structure and feel of the private Propify platform while protecting proprietary information. 
                The "Analyze" tab is interactive in the public preview, while the other sections remain a product and workflow showcase. The full Propify App and Propify AI platform is set to release by the end of the summer.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    tab_analyze, tab_parlays, tab_tracking, tab_learn, tab_account = st.tabs(["Analyze", "Parlays", "Tracking", "Learn", "Account"])
    with tab_analyze:
        render_analyze_tab()
    with tab_parlays:
        p2, p3, p4 = st.tabs(["2-Leg Parlay", "3-Leg Parlay", "4-Leg Parlay"])
        with p2:
            render_locked_parlay_tab(2)
        with p3:
            render_locked_parlay_tab(3)
        with p4:
            render_locked_parlay_tab(4)
    with tab_tracking:
        render_tracking_tab()
    with tab_learn:
        render_learn_tab()
    with tab_account:
        render_account_tab()

# safe logo loading for deployed demo
ICON_PATH = PROPIFY_LOGO_PATH
if ICON_PATH.exists():
    icon_b64 = base64.b64encode(ICON_PATH.read_bytes()).decode("utf-8")
else:
    icon_b64 = ""

def render_header():
    left, right = st.columns([8.4, 1.6])
    with left:
        st.markdown(
            f"""
            <div class="demo-topbar">
                <img src="data:image/png;base64,{icon_b64}" alt="Propify" />
                <div class="demo-topbar-engine">Propify AI Engine Demo</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""<div class="demo-header-note">
                <span class="demo-pill">Public Demo</span>
                <span class="demo-pill">Private analytics blurred</span>
            </div>""",
            unsafe_allow_html=True,
        )

main()
