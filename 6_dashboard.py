import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ============================================================================
# PAGE SETUP
# ============================================================================
st.set_page_config(
    page_title="UrbanCart AI Pricing",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1E293B;
        border-radius: 0.5rem;
        padding: 1rem;
        color: white;
    }
    .positive-growth { color: #10B981 !important; font-weight: bold; }
    .negative-growth { color: #EF4444 !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA LOADING
# ============================================================================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('final_q1_2025_simulation.csv', parse_dates=['Date'])
        params = pd.read_csv('sku_model_params.csv')
        return df, params
    except FileNotFoundError:
        st.error("Data files not found. Please ensure CSV files are in the same directory.")
        return pd.DataFrame(), pd.DataFrame()

df, params_df = load_data()

if df.empty:
    st.stop()

# ============================================================================
# SIDEBAR FILTERS
# ============================================================================
st.sidebar.image("https://img.icons8.com/color/96/000000/shopping-cart--v1.png", width=64)
st.sidebar.title("UrbanCart AI")
st.sidebar.markdown("### Dashboard Filters")

all_categories = sorted(df['Category'].unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Select Categories:",
    options=all_categories,
    default=all_categories
)

min_date = df['Date'].min().date()
max_date = df['Date'].max().date()
selected_dates = st.sidebar.date_input(
    "Select Date Range:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    mask = (df['Category'].isin(selected_categories)) & \
           (df['Date'].dt.date >= start_date) & \
           (df['Date'].dt.date <= end_date)
    filtered_df = df[mask]
else:
    filtered_df = df[df['Category'].isin(selected_categories)]

# Create TABS
tab1, tab2 = st.tabs(["📊 Executive Dashboard", "🧮 What-If Pricing Model"])

# ============================================================================
# TAB 1: EXECUTIVE DASHBOARD
# ============================================================================
with tab1:
    st.title("🛒 AI Dynamic Pricing Engine — Q1 2025 Forecast")
    st.markdown("Explore the financial impact of the new AI pricing strategy across categories and individual SKUs.")

    # Top Level KPIs
    hist_margin = filtered_df['Historical_Margin'].sum()
    sim_margin = filtered_df['Simulated_Margin'].sum()
    margin_growth = (sim_margin / hist_margin - 1) * 100 if hist_margin else 0

    hist_rev = filtered_df['Historical_Revenue'].sum()
    sim_rev = filtered_df['Simulated_Revenue'].sum()
    rev_growth = (sim_rev / hist_rev - 1) * 100 if hist_rev else 0

    hist_vol = filtered_df['Historical_Volume'].sum()
    sim_vol = filtered_df['Simulated_Volume'].sum()
    vol_growth = (sim_vol / hist_vol - 1) * 100 if hist_vol else 0

    col1, col2, col3 = st.columns(3)

    def format_metric(title, hist_val, sim_val, growth_pct, prefix="₹"):
        if prefix == "₹":
            hist_str = f"₹{hist_val/1e6:,.1f}M"
            sim_str = f"₹{sim_val/1e6:,.1f}M"
        else:
            hist_str = f"{hist_val:,.0f}"
            sim_str = f"{sim_val:,.0f}"
            
        color_class = "positive-growth" if growth_pct >= 0 else "negative-growth"
        st.markdown(f"""
        <div class="metric-card">
            <h3 style='margin:0; font-size: 1.1rem; color: #94A3B8;'>{title}</h3>
            <h2 style='margin:5px 0; font-size: 2rem;'>{sim_str}</h2>
            <p style='margin:0;'><span class='{color_class}'>{growth_pct:+.2f}%</span> vs Historical ({hist_str})</p>
        </div>
        <br>
        """, unsafe_allow_html=True)

    with col1:
        format_metric("Total Gross Margin", hist_margin, sim_margin, margin_growth)
    with col2:
        format_metric("Total Revenue", hist_rev, sim_rev, rev_growth)
    with col3:
        format_metric("Total Volume (Units)", hist_vol, sim_vol, vol_growth, prefix="")

    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Category Margin Impact")
        cat_agg = filtered_df.groupby('Category').agg({
            'Historical_Margin': 'sum',
            'Simulated_Margin': 'sum'
        }).reset_index()
        
        fig_cat = go.Figure(data=[
            go.Bar(name='Historical', x=cat_agg['Category'], y=cat_agg['Historical_Margin'], marker_color='#64748B'),
            go.Bar(name='AI-Optimized', x=cat_agg['Category'], y=cat_agg['Simulated_Margin'], marker_color='#10B981')
        ])
        fig_cat.update_layout(barmode='group', plot_bgcolor='rgba(0,0,0,0)', yaxis_title="Margin (INR)", margin=dict(t=10, l=10, r=10, b=10))
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_chart2:
        st.subheader("Daily Revenue Trend")
        daily_agg = filtered_df.groupby('Date').agg({
            'Historical_Revenue': 'sum',
            'Simulated_Revenue': 'sum'
        }).reset_index()
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=daily_agg['Date'], y=daily_agg['Historical_Revenue'], mode='lines', name='Historical', line=dict(color='#64748B')))
        fig_line.add_trace(go.Scatter(x=daily_agg['Date'], y=daily_agg['Simulated_Revenue'], mode='lines', name='AI-Optimized', line=dict(color='#3B82F6')))
        fig_line.update_layout(plot_bgcolor='rgba(0,0,0,0)', yaxis_title="Revenue (INR)", margin=dict(t=10, l=10, r=10, b=10), hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")
    st.subheader("SKU-Level Price vs Margin Trade-off")

    sku_agg = filtered_df.groupby(['SKU', 'Category']).agg({
        'Historical_Price': 'mean',
        'Recommended_Price': 'mean',
        'Historical_Margin': 'sum',
        'Simulated_Margin': 'sum',
        'Historical_Volume': 'sum'
    }).reset_index()

    sku_agg['Price_Change_%'] = (sku_agg['Recommended_Price'] / sku_agg['Historical_Price'] - 1) * 100
    sku_agg['Margin_Change_%'] = (sku_agg['Simulated_Margin'] / sku_agg['Historical_Margin'] - 1) * 100

    fig_scatter = px.scatter(
        sku_agg, x="Price_Change_%", y="Margin_Change_%", color="Category", size="Historical_Volume",
        hover_name="SKU", labels={"Price_Change_%": "Average Price Change (%)", "Margin_Change_%": "Total Margin Change (%)"}
    )
    fig_scatter.add_vline(x=0, line_width=1, line_dash="dash", line_color="gray")
    fig_scatter.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray")
    fig_scatter.update_layout(plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_scatter, use_container_width=True)

# ============================================================================
# TAB 2: WHAT-IF PRICING MODEL
# ============================================================================
with tab2:
    st.title("🧮 Interactive What-If Pricing Model")
    st.markdown("Select a SKU and simulate how changes to the price affect predicted Demand, Revenue, and Gross Margin using the DML Elasticity model.")
    
    col_sel1, col_sel2 = st.columns([1, 2])
    with col_sel1:
        sim_cat = st.selectbox("Select Category", sorted(params_df['Category'].unique()))
    with col_sel2:
        skus_in_cat = params_df[params_df['Category'] == sim_cat]['SKU'].unique().tolist()
        sim_sku = st.selectbox("Select SKU to Model", skus_in_cat)
    
    # Get SKU parameters
    sku_params = params_df[params_df['SKU'] == sim_sku].iloc[0]
    base_cost = sku_params['Base_Cost_INR']
    elasticity = sku_params['Elasticity']
    comp_price = sku_params.get('Mean_Comp_Price', 0)
    
    # Get historical baseline and AI recommended price from df
    sku_hist = df[df['SKU'] == sim_sku]
    avg_hist_price = sku_hist['Historical_Price'].mean()
    avg_hist_vol = sku_hist['Historical_Volume'].mean()
    rec_price = sku_hist['Recommended_Price'].mean() if not sku_hist.empty else avg_hist_price
    
    st.markdown("---")
    
    col_slide, col_metrics = st.columns([1, 1])
    
    with col_slide:
        st.subheader("Adjust Price")
        st.info(f"**Base Cost:** ₹{base_cost:,.2f} | **Price Elasticity:** {elasticity:,.2f}")
        
        # Display markers as text
        st.markdown(f"""
        <div style='background-color:#F8FAFC; color:#0F172A; padding:10px; border-radius:5px; border-left: 4px solid #3B82F6;'>
            <strong>📌 Key Price Points for {sim_sku}:</strong><br>
            • Historical Average: ₹{avg_hist_price:,.2f}<br>
            • Competitor Average: ₹{comp_price:,.2f}<br>
            • <b>AI Recommended: ₹{rec_price:,.2f}</b>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        
        # Tighter slider bounds (-20% to +20% of historical, bounded by cost)
        min_price = max(base_cost, avg_hist_price * 0.8)
        max_price = avg_hist_price * 1.2
        
        proposed_price = st.slider(
            "Proposed Listed Price (INR)",
            min_value=float(min_price),
            max_value=float(max_price),
            value=float(avg_hist_price),
            step=5.0
        )
        
        # Calculate impacts using log-log elasticity
        predicted_vol = avg_hist_vol * ((proposed_price / avg_hist_price) ** elasticity)
        predicted_rev = proposed_price * predicted_vol
        predicted_margin = (proposed_price - base_cost) * predicted_vol
        
        hist_rev_daily = avg_hist_price * avg_hist_vol
        hist_margin_daily = (avg_hist_price - base_cost) * avg_hist_vol
        
    with col_metrics:
        st.subheader("Predicted Daily Impact")
        
        def display_sim_metric(label, pred_val, hist_val, is_currency=True):
            pct_change = (pred_val / hist_val - 1) * 100 if hist_val else 0
            val_str = f"₹{pred_val:,.0f}" if is_currency else f"{pred_val:,.0f}"
            color = "green" if pct_change >= 0 else "red"
            st.markdown(f"**{label}:** {val_str} (<span style='color:{color}; font-weight:bold'>{pct_change:+.2f}%</span> vs Hist.)", unsafe_allow_html=True)
            
        display_sim_metric("Predicted Daily Volume", predicted_vol, avg_hist_vol, is_currency=False)
        display_sim_metric("Predicted Daily Revenue", predicted_rev, hist_rev_daily)
        display_sim_metric("Predicted Daily Margin", predicted_margin, hist_margin_daily)
        
        if elasticity > -1.0:
            st.warning("⚠️ **Inelastic Product:** Increasing the price will ALWAYS increase revenue because demand drops slower than the price rises.")
        elif elasticity < -2.0:
            st.error("🚨 **Highly Elastic Product:** Customers are extremely sensitive to price increases. Raise prices cautiously to avoid collapsing volume.")
        else:
            st.success("✅ **Standard Elasticity:** Customers show normal sensitivity to price changes.")
