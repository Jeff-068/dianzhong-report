import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ── Page Config ──
st.set_page_config(
    page_title="点众漫剧 · 数据分析报告",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load Data ──
@st.cache_data
def load_data():
    df = pd.read_excel("data.xlsx")
    # Convert Excel serial dates
    if df["日期"].dtype in ["float64", "int64"]:
        df["日期"] = pd.to_datetime("1899-12-30") + pd.to_timedelta(df["日期"].astype(int), unit="D")
    else:
        df["日期"] = pd.to_datetime(df["日期"])
    df.columns = ["日期", "项目", "短剧类型", "消耗", "现金消耗", "24h_ROI", "当日变现", "实际变现", "利润"]
    return df

df = load_data()

# ── Sidebar Filters ──
st.sidebar.title("📊 筛选条件")
date_range = st.sidebar.date_input(
    "日期范围",
    value=(df["日期"].min().date(), df["日期"].max().date()),
    min_value=df["日期"].min().date(),
    max_value=df["日期"].max().date(),
)
type_filter = st.sidebar.multiselect(
    "短剧类型", options=df["短剧类型"].unique().tolist(), default=df["短剧类型"].unique().tolist()
)

# Apply filters
if len(date_range) == 2:
    mask = (
        (df["日期"].dt.date >= date_range[0])
        & (df["日期"].dt.date <= date_range[1])
        & (df["短剧类型"].isin(type_filter))
    )
else:
    mask = df["短剧类型"].isin(type_filter)
fdf = df[mask].copy()

# ── Header ──
st.markdown(
    """
    <div style="text-align:center; padding: 10px 0 20px 0;">
        <h1 style="margin-bottom:4px;">点众漫剧 · 端原生分销数据分析</h1>
        <p style="color:gray; font-size:15px;">
            数据周期：{} — {} ｜ 项目：点众分销-端原生
        </p>
    </div>
    """.format(
        fdf["日期"].min().strftime("%Y-%m-%d") if len(fdf) else "-",
        fdf["日期"].max().strftime("%Y-%m-%d") if len(fdf) else "-",
    ),
    unsafe_allow_html=True,
)

# ── KPI Metrics ──
total_spend = fdf["消耗"].sum()
total_cash = fdf["现金消耗"].sum()
total_revenue = fdf["实际变现"].sum()
total_profit = fdf["利润"].sum()
overall_roi = total_revenue / total_cash if total_cash > 0 else 0
profit_rate = total_profit / total_spend * 100 if total_spend > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("总消耗", f"{total_spend:,.2f}", help="投放总消耗金额")
c2.metric("总实际变现", f"{total_revenue:,.2f}", help="实际结算变现金额")
c3.metric("总利润", f"{total_profit:,.2f}", delta=f"{profit_rate:.1f}%")
c4.metric("整体 ROI", f"{overall_roi:.4f}", delta="盈亏线=1.0", delta_color="off")

st.divider()

# ── Daily Aggregation ──
daily = fdf.groupby("日期").agg(
    消耗=("消耗", "sum"),
    现金消耗=("现金消耗", "sum"),
    实际变现=("实际变现", "sum"),
    利润=("利润", "sum"),
    当日变现=("当日变现", "sum"),
).reset_index()
daily["ROI"] = daily.apply(lambda r: r["实际变现"] / r["现金消耗"] if r["现金消耗"] > 0 else 0, axis=1)
daily["日期标签"] = daily["日期"].dt.strftime("%-m/%-d")

# ── Phase Tagging ──
def get_phase(d):
    if d <= pd.Timestamp("2026-03-16"):
        return "冷启动期 (3/12-3/16)"
    elif d <= pd.Timestamp("2026-03-27"):
        return "测试期 (3/17-3/27)"
    else:
        return "放量期 (3/28-3/30)"

daily["阶段"] = daily["日期"].apply(get_phase)

# ── Charts Row 1 ──
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("每日消耗 vs 实际变现")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=daily["日期标签"], y=daily["消耗"], name="消耗",
        fill="tozeroy", line=dict(color="#4361ee"),
    ))
    fig1.add_trace(go.Scatter(
        x=daily["日期标签"], y=daily["实际变现"], name="实际变现",
        fill="tozeroy", line=dict(color="#2ec4b6"),
    ))
    fig1.update_layout(height=350, yaxis_type="log", yaxis_title="金额 (log)", margin=dict(t=10))
    st.plotly_chart(fig1, use_container_width=True)

with col_right:
    st.subheader("每日利润趋势")
    colors = ["#2ec4b6" if v >= 0 else "#e63946" for v in daily["利润"]]
    fig2 = go.Figure(go.Bar(
        x=daily["日期标签"], y=daily["利润"], marker_color=colors,
    ))
    fig2.update_layout(height=350, yaxis_title="利润", margin=dict(t=10))
    st.plotly_chart(fig2, use_container_width=True)

# ── Charts Row 2 ──
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("每日 ROI 走势")
    roi_colors = ["#2ec4b6" if v >= 1 else "#e63946" for v in daily["ROI"]]
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=daily["日期标签"], y=daily["ROI"], mode="lines+markers",
        line=dict(color="#f77f00"), marker=dict(color=roi_colors, size=8),
        fill="tozeroy", fillcolor="rgba(247,127,0,0.08)",
    ))
    fig3.add_hline(y=1.0, line_dash="dash", line_color="red",
                   annotation_text="盈亏平衡线 ROI=1.0", annotation_position="top right")
    fig3.update_layout(height=350, yaxis_title="ROI", yaxis_range=[0, min(daily["ROI"].max() * 1.2, 3)], margin=dict(t=10))
    st.plotly_chart(fig3, use_container_width=True)

with col_right2:
    st.subheader("漫剧 vs 非漫剧 对比")
    type_agg = fdf.groupby("短剧类型").agg(
        消耗=("消耗", "sum"), 实际变现=("实际变现", "sum"), 利润=("利润", "sum")
    ).reset_index()
    fig4 = go.Figure()
    for col, color in [("消耗", "#4361ee"), ("实际变现", "#2ec4b6"), ("利润", "#e63946")]:
        fig4.add_trace(go.Bar(name=col, x=type_agg["短剧类型"], y=type_agg[col], marker_color=color))
    fig4.update_layout(barmode="group", height=350, yaxis_title="金额", margin=dict(t=10))
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ── Phase Analysis Table ──
st.subheader("阶段分析")

phase_agg = daily.groupby("阶段").agg(
    总消耗=("消耗", "sum"),
    实际变现=("实际变现", "sum"),
    利润=("利润", "sum"),
    现金消耗=("现金消耗", "sum"),
).reset_index()
phase_agg["ROI"] = phase_agg["实际变现"] / phase_agg["现金消耗"]
phase_agg["消耗占比"] = (phase_agg["总消耗"] / phase_agg["总消耗"].sum() * 100).round(2).astype(str) + "%"
phase_agg["ROI"] = phase_agg["ROI"].round(4)
phase_agg["状态"] = phase_agg["利润"].apply(lambda x: "✅ 盈利" if x > 0 else ("⚠️ 改善中" if x > -1000 else "❌ 亏损"))

st.dataframe(
    phase_agg[["阶段", "总消耗", "实际变现", "利润", "ROI", "消耗占比", "状态"]].style.format(
        {"总消耗": "{:,.2f}", "实际变现": "{:,.2f}", "利润": "{:,.2f}", "ROI": "{:.4f}"}
    ),
    use_container_width=True,
    hide_index=True,
)

# ── Scale Period Deep Dive ──
st.subheader("放量期 ROI 日变化（3/28 - 3/30）")

scale_df = daily[daily["日期"] >= pd.Timestamp("2026-03-28")].copy()
if len(scale_df) > 0:
    fig5 = make_subplots(specs=[[{"secondary_y": True}]])
    fig5.add_trace(go.Bar(name="消耗", x=scale_df["日期标签"], y=scale_df["消耗"], marker_color="#4361ee"), secondary_y=False)
    fig5.add_trace(go.Bar(name="实际变现", x=scale_df["日期标签"], y=scale_df["实际变现"], marker_color="#2ec4b6"), secondary_y=False)
    fig5.add_trace(go.Scatter(name="ROI", x=scale_df["日期标签"], y=scale_df["ROI"],
                              mode="lines+markers+text", text=scale_df["ROI"].round(2).astype(str),
                              textposition="top center", line=dict(color="#f77f00", width=3),
                              marker=dict(size=10)), secondary_y=True)
    fig5.update_layout(height=380, barmode="group", margin=dict(t=10))
    fig5.update_yaxes(title_text="金额", secondary_y=False)
    fig5.update_yaxes(title_text="ROI", range=[0, 1.2], secondary_y=True)
    st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ── Type Breakdown ──
st.subheader("漫剧 vs 非漫剧 明细")

type_detail = fdf.groupby("短剧类型").agg(
    总消耗=("消耗", "sum"),
    现金消耗=("现金消耗", "sum"),
    实际变现=("实际变现", "sum"),
    利润=("利润", "sum"),
).reset_index()
type_detail["ROI"] = type_detail["实际变现"] / type_detail["现金消耗"]
type_detail["消耗占比"] = (type_detail["总消耗"] / type_detail["总消耗"].sum() * 100).round(2).astype(str) + "%"

st.dataframe(
    type_detail.style.format(
        {"总消耗": "{:,.2f}", "现金消耗": "{:,.2f}", "实际变现": "{:,.2f}", "利润": "{:,.2f}", "ROI": "{:.4f}"}
    ),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# ── Key Insights ──
st.subheader("核心发现与建议")

ic1, ic2 = st.columns(2)
with ic1:
    st.info("**1. 项目处于快速放量初期**\n\n3/28-3/30 三天消耗占总消耗 95.8%，项目刚进入大规模投放阶段。3/18 首次大额消耗 ROI 仅 0.44，3/30 ROI 已回升至 0.96，趋势向好。")
    st.error("**3. 非漫剧 ROI 显著偏低**\n\n非漫剧整体 ROI 仅 0.48，远低于漫剧 0.83。建议暂停或缩减非漫剧投放，将预算集中在漫剧品类。")
    st.warning("**5. 结算折扣率约 5%**\n\n实际变现 ≈ 当日变现 × 0.95，ROI 至少需达到 1.08 才能覆盖消耗+折扣实现真正盈利。")

with ic2:
    st.success("**2. ROI 持续改善，趋近盈亏平衡**\n\n放量期 ROI 从 3/28 的 0.50 → 3/29 的 0.65 → 3/30 的 0.96，三天连续提升。预计短期内可突破 1.0 的盈亏线。")
    st.success("**4. 消耗与变现强相关**\n\n3/30 消耗 27,694，当日变现 25,943，变现跟随率 93.7%。素材质量和变现路径健康，放量未导致 ROI 崩塌。")
    st.info("**6. 下一步行动建议**\n\n① 持续监控日 ROI，目标突破 1.0\n② 砍掉非漫剧投放线\n③ 关注 LT 长期变现数据验证回收能力")

st.divider()

# ── Raw Data ──
with st.expander("📋 查看原始数据"):
    display_df = fdf.copy()
    display_df["日期"] = display_df["日期"].dt.strftime("%Y-%m-%d")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Footer ──
st.markdown(
    "<div style='text-align:center; color:gray; padding:20px; font-size:13px;'>"
    "点众分销-端原生 · 数据分析报告 · 2026年3月"
    "</div>",
    unsafe_allow_html=True,
)
