import os
from datetime import datetime
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel
from groq import Groq

load_dotenv()

FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# --- Page Config ---
st.set_page_config(
    page_title="PagePulse · Social Sentiment Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Custom Human-Crafted SaaS CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hide default Streamlit header/footer clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent;}

    .stApp {
        background-color: #0B0F19;
        color: #F1F5F9;
    }

    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Top Header Bar */
    .hero-wrap {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
        padding-bottom: 1.25rem;
        border-bottom: 1px solid #1E293B;
    }
    .hero-title {
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        color: #F8FAFC;
        margin: 0;
    }
    .hero-sub {
        font-size: 0.9rem;
        color: #94A3B8;
        margin-top: 0.25rem;
    }

    /* Custom KPI Cards */
    .kpi-card {
        background: linear-gradient(145deg, #111827, #0F172A);
        border: 1px solid #1E293B;
        border-radius: 14px;
        padding: 1.25rem 1.4rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .kpi-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94A3B8;
        margin-bottom: 0.45rem;
    }
    .kpi-value {
        font-size: 1.95rem;
        font-weight: 700;
        color: #F8FAFC;
        line-height: 1.1;
    }
    .kpi-foot {
        font-size: 0.8rem;
        color: #64748B;
        margin-top: 0.4rem;
    }

    /* Post Feed Cards */
    .post-card {
        background-color: #111827;
        border: 1px solid #1E293B;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s ease;
    }
    .post-card:hover {
        border-color: #334155;
    }
    .post-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        margin-bottom: 0.75rem;
    }
    .post-caption {
        font-size: 1.12rem;
        font-weight: 600;
        color: #F8FAFC;
        line-height: 1.45;
    }
    .post-meta {
        font-size: 0.8rem;
        color: #64748B;
        margin-bottom: 1rem;
    }
    .summary-box {
        background-color: #0B0F19;
        border-left: 3px solid #6366F1;
        padding: 0.85rem 1rem;
        border-radius: 0 10px 10px 0;
        font-size: 0.92rem;
        color: #CBD5E1;
        line-height: 1.5;
        margin-bottom: 0.75rem;
    }

    /* Sentiment Badges */
    .badge {
        display: inline-block;
        padding: 0.28rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        white-space: nowrap;
    }
    .badge-pos { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-neg { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-mix { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-neu { background: rgba(148, 163, 184, 0.15); color: #CBD5E1; border: 1px solid rgba(148, 163, 184, 0.3); }

    /* Comment Rows */
    .comment-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.6rem 0.85rem;
        background: #0B0F19;
        border: 1px solid #1E293B;
        border-radius: 10px;
        margin-bottom: 0.45rem;
        font-size: 0.9rem;
        color: #E2E8F0;
    }

    /* Primary Button */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4F46E5, #6366F1);
        border: none;
        border-radius: 10px;
        padding: 0.55rem 1.25rem;
        font-weight: 600;
        color: white;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4338CA, #4F46E5);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Structured Output Schema ---
class CommentSentiment(BaseModel):
    comment: str
    sentiment: str  # "Positive", "Negative", or "Neutral"

class PostReviewAnalysis(BaseModel):
    overall_sentiment: str  # "Positive", "Negative", "Mixed", or "No Comments"
    summary: str
    comment_breakdown: list[CommentSentiment]

def format_timestamp(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y · %I:%M %p")
    except Exception:
        return iso_str

def badge_html(sentiment: str) -> str:
    s = sentiment.lower()
    if "pos" in s:
        cls = "badge-pos"
    elif "neg" in s:
        cls = "badge-neg"
    elif "mix" in s:
        cls = "badge-mix"
    else:
        cls = "badge-neu"
    return f'<span class="badge {cls}">{sentiment}</span>'

def fetch_facebook_posts():
    url = "https://graph.facebook.com/v27.0/me/feed"
    params = {
        "fields": "id,message,created_time,reactions.summary(true),comments{message,created_time}",
        "access_token": FB_PAGE_TOKEN,
    }
    res = requests.get(url, params=params, timeout=15)
    if not res.ok:
        raise RuntimeError(f"{res.status_code}: {res.json()}")
    return res.json().get("data", [])

def analyze_post_comments(post_text: str, comments: list[str]) -> PostReviewAnalysis:
    if not comments:
        return PostReviewAnalysis(
            overall_sentiment="No Comments",
            summary="No comments available to analyze on this post yet.",
            comment_breakdown=[],
        )

    prompt = (
        f"Post caption: {post_text or '[No text]'}\n\n"
        f"Comments:\n" + "\n".join(f"- {c}" for c in comments)
    )

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Analyze the Facebook comments on this post. Comments may be written in English, "
                    "Nepali (Devanagari script, e.g., 'राम्रो छ', 'बकवास'), Romanized Nepali (Nepali written "
                    "using English letters, e.g., 'ramro cha', 'kasto hawa', 'babbal', 'jhyau'), or "
                    "code-mixed Nepali-English. Understand local Nepali slang, tone, and sarcasm accurately. "
                    "Keep the original comment text unchanged in the output, classify each comment strictly "
                    "as 'Positive', 'Negative', or 'Neutral', determine the overall review sentiment "
                    "('Positive', 'Negative', or 'Mixed'), and write a concise 1-2 sentence summary in English."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "post_review_analysis",
                "schema": PostReviewAnalysis.model_json_schema(),
            },
        },
        temperature=0.1,
    )

    return PostReviewAnalysis.model_validate_json(completion.choices[0].message.content)

# --- Header ---
col_head, col_btn = st.columns([4, 1])
with col_head:
    st.markdown(
        """
        <div class="hero-wrap" style="border:none; margin-bottom:0; padding-bottom:0;">
            <div>
                <h1 class="hero-title">PagePulse Analytics</h1>
                <p class="hero-sub">Real-time Facebook Page engagement & AI comment sentiment intelligence</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_btn:
    st.write("")
    run_sync = st.button("↻ Sync & Analyze", type="primary", use_container_width=True)

st.markdown("<hr style='border-color:#1E293B; margin-top:0.5rem; margin-bottom:1.5rem;'>", unsafe_allow_html=True)

if not all([FB_PAGE_TOKEN, GROQ_API_KEY]):
    st.error("Missing credentials in .env! Ensure FB_PAGE_TOKEN and GROQ_API_KEY are set.")
    st.stop()

# Empty-state callout — shown only before the first sync
if "analyzed_posts" not in st.session_state and not run_sync:
    st.markdown(
        """
        <div style="
            background: linear-gradient(145deg, #111827, #0F172A);
            border: 1px solid #1E293B;
            border-radius: 16px;
            padding: 2.5rem 2rem;
            text-align: center;
            max-width: 560px;
            margin: 3rem auto;
            box-shadow: 0 8px 32px rgba(0,0,0,0.35);
        ">
            <div style="font-size: 2.75rem; margin-bottom: 1rem;">📡</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.6rem;">
                No data loaded yet
            </div>
            <div style="font-size: 0.95rem; color: #94A3B8; line-height: 1.6; margin-bottom: 1.5rem;">
                Click <strong style="color:#818CF8;">↻ Sync &amp; Analyze</strong> in the top-right corner
                to fetch your Facebook Page feed and run AI-powered sentiment analysis on every post's comments.
            </div>
            <div style="
                display: inline-block;
                background: rgba(99,102,241,0.12);
                border: 1px solid rgba(99,102,241,0.3);
                border-radius: 9999px;
                padding: 0.4rem 1.1rem;
                font-size: 0.82rem;
                font-weight: 600;
                color: #818CF8;
                letter-spacing: 0.04em;
            ">↻ Sync &amp; Analyze to get started</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# Fetch & cache results in session_state
if run_sync:
    with st.spinner("Syncing Facebook feed & classifying audience sentiment..."):
        try:
            raw_posts = fetch_facebook_posts()
        except Exception as e:
            st.error(f"Facebook API Error: {e}")
            st.stop()

        results = []
        for post in raw_posts:
            caption = post.get("message", "(Media / Link Post)")
            likes = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
            raw_comments = [
                c.get("message", "")
                for c in post.get("comments", {}).get("data", [])
                if c.get("message")
            ]
            analysis = analyze_post_comments(caption, raw_comments)
            results.append(
                {
                    "id": post.get("id"),
                    "caption": caption,
                    "created_time": format_timestamp(post.get("created_time", "")),
                    "likes": likes,
                    "comment_count": len(raw_comments),
                    "analysis": analysis,
                }
            )
        st.session_state["analyzed_posts"] = results

posts_data = st.session_state.get("analyzed_posts", [])

if not posts_data:
    st.info("No posts found on this Page yet. Publish a post on Facebook and click Sync & Analyze.")
    st.stop()

# --- Aggregate Metrics ---
total_posts = len(posts_data)
total_likes = sum(p["likes"] for p in posts_data)
total_comments = sum(p["comment_count"] for p in posts_data)

sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
for p in posts_data:
    for item in p["analysis"].comment_breakdown:
        key = item.sentiment.capitalize()
        if key in sentiment_counts:
            sentiment_counts[key] += 1

pos_rate = (
    round((sentiment_counts["Positive"] / total_comments) * 100)
    if total_comments > 0
    else 0
)

# --- Top 4 KPI Cards ---
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">Posts Tracked</div>'
        f'<div class="kpi-value">{total_posts}</div>'
        f'<div class="kpi-foot">Active Page feed items</div></div>',
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">Total Reactions</div>'
        f'<div class="kpi-value">{total_likes}</div>'
        f'<div class="kpi-foot">Likes & emoji reactions</div></div>',
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">Comments Analyzed</div>'
        f'<div class="kpi-value">{total_comments}</div>'
        f'<div class="kpi-foot">{sentiment_counts["Positive"]} pos · {sentiment_counts["Negative"]} neg · {sentiment_counts["Neutral"]} neu</div></div>',
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">Approval Score</div>'
        f'<div class="kpi-value">{pos_rate}%</div>'
        f'<div class="kpi-foot">Positive comment share</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# --- Interactive Graphs Section ---
chart_col1, chart_col2 = st.columns([1, 1.4])

with chart_col1:
    st.markdown("##### Comment Sentiment Breakdown")
    fig_donut = go.Figure(
        data=[
            go.Pie(
                labels=list(sentiment_counts.keys()),
                values=list(sentiment_counts.values()),
                hole=0.62,
                marker=dict(colors=["#10B981", "#EF4444", "#64748B"]),
                textinfo="label+percent",
                textfont=dict(color="#F8FAFC", size=12),
                hovertemplate="<b>%{label}</b><br>Comments: %{value}<br>Share: %{percent}<extra></extra>",
            )
        ]
    )
    fig_donut.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#CBD5E1", family="Inter"),
        margin=dict(t=20, b=20, l=20, r=20),
        height=310,
        showlegend=False,
        annotations=[
            dict(
                text=f"<b>{total_comments}</b><br>Comments",
                x=0.5,
                y=0.5,
                font_size=15,
                font_color="#F8FAFC",
                showarrow=False,
            )
        ],
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with chart_col2:
    st.markdown("##### Engagement by Post (Reactions vs. Comments)")
    df_posts = pd.DataFrame(
        [
            {
                "Post": (p["caption"][:28] + "...") if len(p["caption"]) > 28 else p["caption"],
                "Reactions": p["likes"],
                "Comments": p["comment_count"],
                "Sentiment": p["analysis"].overall_sentiment,
            }
            for p in posts_data
        ]
    )
    fig_bar = go.Figure()
    fig_bar.add_trace(
        go.Bar(
            name="Reactions",
            x=df_posts["Post"],
            y=df_posts["Reactions"],
            marker_color="#6366F1",
            marker_cornerradius=6,
        )
    )
    fig_bar.add_trace(
        go.Bar(
            name="Comments",
            x=df_posts["Post"],
            y=df_posts["Comments"],
            marker_color="#38BDF8",
            marker_cornerradius=6,
        )
    )
    fig_bar.update_layout(
        barmode="group",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#CBD5E1", family="Inter"),
        margin=dict(t=25, b=25, l=25, r=25),
        height=310,
        xaxis=dict(showgrid=False, tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#1E293B", dtick=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("<hr style='border-color:#1E293B; margin:1.25rem 0;'>", unsafe_allow_html=True)

# --- Post Breakdown Feed ---
st.markdown("##### Post-by-Post AI Audit")
for p in posts_data:
    analysis = p["analysis"]
    st.markdown(
        f"""
        <div class="post-card">
            <div class="post-header">
                <div class="post-caption">{p["caption"]}</div>
                <div>{badge_html(analysis.overall_sentiment)}</div>
            </div>
            <div class="post-meta">
                Published {p["created_time"]} &nbsp;·&nbsp; ❤️ {p["likes"]} Reactions &nbsp;·&nbsp; 💬 {p["comment_count"]} Comments
            </div>
            <div class="summary-box">
                <strong>AI Verdict:</strong> {analysis.summary}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if analysis.comment_breakdown:
        with st.expander(f"Inspect {len(analysis.comment_breakdown)} classified comments"):
            for item in analysis.comment_breakdown:
                st.markdown(
                    f"""
                    <div class="comment-row">
                        <span>{item.comment}</span>
                        <span>{badge_html(item.sentiment)}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )