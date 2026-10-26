
import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from pathlib import Path
from io import BytesIO

st.set_page_config(
    page_title="Business KPI Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("Interactive Business Dashboard")
st.caption("Executive KPI monitoring | Sales | Customer Analytics")

# Load the project dataset
DATA_FILE = Path(__file__).parent / "business_data.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_FILE)
    df["month"] = pd.to_datetime(df["month"])
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("Dashboard Filters")

months = sorted(df["month"].dt.strftime("%Y-%m").unique())
selected_months = st.sidebar.multiselect(
    "Select months",
    months,
    default=months
)

regions = st.sidebar.multiselect(
    "Select regions",
    sorted(df["region"].unique()),
    default=sorted(df["region"].unique())
)

categories = st.sidebar.multiselect(
    "Select categories",
    sorted(df["category"].unique()),
    default=sorted(df["category"].unique())
)

filtered = df[
    df["month"].dt.strftime("%Y-%m").isin(selected_months)
    & df["region"].isin(regions)
    & df["category"].isin(categories)
].copy()

if filtered.empty:
    st.warning("No records match these filters. Select different options.")
    st.stop()

# Calculate KPIs from the selected data
revenue = filtered["revenue"].sum()
orders = filtered["orders"].sum()
new_customers = filtered["new_customers"].sum()
marketing_spend = filtered["acquisition_spend"].sum()
customers_start = filtered["customers_at_start"].sum()
customers_lost = filtered["customers_lost"].sum()

cac = marketing_spend / new_customers if new_customers else 0
aov = revenue / orders if orders else 0
churn = customers_lost / customers_start * 100 if customers_start else 0

# KPI cards
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", f"${revenue:,.0f}")
c2.metric("Acquisition Cost (CAC)", f"${cac:,.2f}")
c3.metric("Customer Churn", f"{churn:.2f}%")
c4.metric("Average Order Value", f"${aov:,.2f}")

st.divider()

# Aggregate data for charts
monthly = (
    filtered.groupby("month", as_index=False)
    .agg(revenue=("revenue", "sum"))
    .sort_values("month")
)

left, right = st.columns(2)

with left:
    st.subheader("Revenue Trend")
    fig = px.area(
        monthly,
        x="month",
        y="revenue",
        markers=True,
        title="Monthly Revenue"
    )
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Revenue ($)"
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Revenue by Category")
    category_data = (
        filtered.groupby("category", as_index=False)
        .agg(revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
    )
    fig = px.bar(
        category_data,
        x="category",
        y="revenue",
        color="category",
        title="Category Performance"
    )
    st.plotly_chart(fig, use_container_width=True)

# Geographic visualization
st.subheader("Geographic Revenue Map")
geo_data = (
    filtered.groupby("region", as_index=False)
    .agg(revenue=("revenue", "sum"))
)

fig_map = px.choropleth(
    geo_data,
    locations="region",
    locationmode="country names",
    color="revenue",
    hover_name="region",
    color_continuous_scale="Blues",
    title="Revenue by Country"
)
fig_map.update_geos(showframe=False, showcoastlines=True)
st.plotly_chart(fig_map, use_container_width=True)

# Region and month heatmap
st.subheader("Regional Revenue Heatmap")
heat_data = filtered.copy()
heat_data["month_label"] = heat_data["month"].dt.strftime("%Y-%m")
pivot = heat_data.pivot_table(
    index="region",
    columns="month_label",
    values="revenue",
    aggfunc="sum",
    fill_value=0
)
fig_heat = px.imshow(
    pivot,
    aspect="auto",
    color_continuous_scale="Blues",
    labels=dict(x="Month", y="Region", color="Revenue"),
    title="Revenue by Region and Month"
)
st.plotly_chart(fig_heat, use_container_width=True)

# Detailed data table
st.subheader("Filtered Business Data")
st.dataframe(
    filtered.sort_values("month"),
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "Download filtered data (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_business_data.csv",
    mime="text/csv"
)

# PDF proof generated from the current dashboard selection
def create_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Business KPI Dashboard Report", new_x="LMARGIN",
             new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(
        0, 7,
        "Reporting period: "
        + (", ".join(selected_months) if selected_months else "None")
    )
    pdf.multi_cell(
        0, 7,
        "Regions: " + (", ".join(regions) if regions else "None")
    )
    pdf.multi_cell(
        0, 7,
        "Categories: " + (", ".join(categories) if categories else "None")
    )
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Executive KPIs", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)

    report_lines = [
        f"Total Revenue: ${revenue:,.2f}",
        f"Customer Acquisition Cost: ${cac:,.2f}",
        f"Customer Churn Rate: {churn:.2f}%",
        f"Average Order Value: ${aov:,.2f}",
        f"Orders: {orders:,}",
        f"New Customers: {new_customers:,}"
    ]
    for line in report_lines:
        pdf.cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Revenue by Category", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for _, row in category_data.iterrows():
        pdf.multi_cell(
            0, 7, f"{row['category']}: ${row['revenue']:,.2f}"
        )

    pdf.ln(3)
    pdf.set_font("Helvetica", size=9)
    pdf.multi_cell(
        0, 6,
        "Note: This report uses illustrative sample data for portfolio "
        "demonstration. Figures are not verified company results. "
        "Churn is calculated as customers lost divided by the sum of "
        "the supplied starting-customer counts in the selected records."
    )
    return bytes(pdf.output())

st.download_button(
    "Download Dashboard Report (PDF)",
    data=create_pdf(),
    file_name="dashboard_report.pdf",
    mime="application/pdf"
)

st.caption(
    "Portfolio demonstration | Data is illustrative | "
    "Built with Python, Streamlit and Plotly"
)
