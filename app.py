
import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from pathlib import Path

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="Business KPI Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("Interactive Business Dashboard")
st.caption("Executive KPI Monitoring | Sales | Customer Analytics")

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
DATA_FILE = Path(__file__).parent / "business_data.csv"


@st.cache_data
def load_data():
    data = pd.read_csv(DATA_FILE)

    required_columns = [
        "month", "region", "category", "revenue", "orders",
        "new_customers", "acquisition_spend",
        "customers_at_start", "customers_lost"
    ]

    missing_columns = [
        col for col in required_columns if col not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns in business_data.csv: {missing_columns}"
        )

    data["month"] = pd.to_datetime(data["month"], errors="coerce")
    data = data.dropna(subset=["month"]).copy()

    numeric_columns = [
        "revenue", "orders", "new_customers", "acquisition_spend",
        "customers_at_start", "customers_lost"
    ]

    for col in numeric_columns:
        data[col] = pd.to_numeric(
            data[col], errors="coerce"
        ).fillna(0)

    return data


try:
    df = load_data()
except Exception as error:
    st.error(f"Unable to load business_data.csv: {error}")
    st.stop()

if df.empty:
    st.error("The dataset is empty or contains no valid dates.")
    st.stop()

# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("Dashboard Filters")

months = sorted(df["month"].dt.strftime("%Y-%m").unique())
all_regions = sorted(df["region"].dropna().unique().tolist())
all_categories = sorted(df["category"].dropna().unique().tolist())

selected_months = st.sidebar.multiselect(
    "Select months",
    months,
    default=months
)

regions = st.sidebar.multiselect(
    "Select regions",
    all_regions,
    default=all_regions
)

categories = st.sidebar.multiselect(
    "Select categories",
    all_categories,
    default=all_categories
)

filtered = df[
    df["month"].dt.strftime("%Y-%m").isin(selected_months)
    & df["region"].isin(regions)
    & df["category"].isin(categories)
].copy()

if filtered.empty:
    st.warning(
        "No records match your filters. "
        "Please select at least one month, region and category."
    )
    st.stop()

# --------------------------------------------------
# KPI CALCULATIONS
# --------------------------------------------------
revenue = filtered["revenue"].sum()
orders = filtered["orders"].sum()
new_customers = filtered["new_customers"].sum()
marketing_spend = filtered["acquisition_spend"].sum()
customers_start = filtered["customers_at_start"].sum()
customers_lost = filtered["customers_lost"].sum()

cac = marketing_spend / new_customers if new_customers else 0
aov = revenue / orders if orders else 0

churn = (
    customers_lost / customers_start * 100
    if customers_start else 0
)

# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Revenue", f"${revenue:,.0f}")
c2.metric("Acquisition Cost (CAC)", f"${cac:,.2f}")
c3.metric("Customer Churn", f"{churn:.2f}%")
c4.metric("Average Order Value", f"${aov:,.2f}")

st.divider()

# --------------------------------------------------
# REVENUE TREND
# --------------------------------------------------
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
        yaxis_title="Revenue ($)",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# REVENUE BY CATEGORY
# --------------------------------------------------
category_data = (
    filtered.groupby("category", as_index=False)
    .agg(revenue=("revenue", "sum"))
    .sort_values("revenue", ascending=False)
)

with right:
    st.subheader("Revenue by Category")

    fig = px.bar(
        category_data,
        x="category",
        y="revenue",
        color="category",
        title="Category Performance",
        labels={
            "revenue": "Revenue ($)",
            "category": "Category"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# GEOGRAPHIC REVENUE MAP
# --------------------------------------------------
st.subheader("Geographic Revenue Map")

country_names = {
    "USA": "United States",
    "UK": "United Kingdom",
    "UAE": "United Arab Emirates"
}

geo_data = (
    filtered.groupby("region", as_index=False)
    .agg(revenue=("revenue", "sum"))
)

geo_data["country"] = geo_data["region"].replace(country_names)

fig_map = px.choropleth(
    geo_data,
    locations="country",
    locationmode="country names",
    color="revenue",
    hover_name="country",
    color_continuous_scale="Blues",
    title="Revenue by Country",
    labels={"revenue": "Revenue ($)"}
)

fig_map.update_geos(
    showframe=False,
    showcoastlines=True
)

st.plotly_chart(fig_map, use_container_width=True)

# --------------------------------------------------
# REGIONAL REVENUE HEATMAP
# --------------------------------------------------
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
    labels={
        "x": "Month",
        "y": "Region",
        "color": "Revenue ($)"
    },
    title="Revenue by Region and Month"
)

st.plotly_chart(fig_heat, use_container_width=True)

# --------------------------------------------------
# FILTERED DATA TABLE
# --------------------------------------------------
st.subheader("Filtered Business Data")

st.dataframe(
    filtered.sort_values("month"),
    use_container_width=True,
    hide_index=True
)

# --------------------------------------------------
# CSV DOWNLOAD
# --------------------------------------------------
st.download_button(
    label="Download Filtered Data (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_business_data.csv",
    mime="text/csv",
    key="filtered_csv_download"
)

# --------------------------------------------------
# PDF REPORT
# --------------------------------------------------
def create_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Write each line from the left page margin.
    def write_line(text, height=7):
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            w=pdf.epw,
            h=height,
            text=str(text),
            new_x="LMARGIN",
            new_y="NEXT"
        )

    # Report title
    pdf.set_font("Helvetica", "B", 18)
    write_line("Business KPI Dashboard Report", 12)

    # Selected filters
    pdf.set_font("Helvetica", size=10)

    write_line(
        "Reporting period: "
        + (", ".join(selected_months) if selected_months else "None")
    )

    write_line(
        "Regions: "
        + (", ".join(map(str, regions)) if regions else "None")
    )

    write_line(
        "Categories: "
        + (", ".join(map(str, categories)) if categories else "None")
    )

    # Executive KPI summary
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    write_line("Executive KPIs", 9)

    pdf.set_font("Helvetica", size=10)
    write_line(f"Total Revenue: ${revenue:,.2f}")
    write_line(f"Customer Acquisition Cost (CAC): ${cac:,.2f}")
    write_line(f"Customer Churn: {churn:.2f}%")
    write_line(f"Average Order Value: ${aov:,.2f}")

    # Revenue by category
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    write_line("Revenue by Category", 9)

    pdf.set_font("Helvetica", size=10)

    for _, row in category_data.iterrows():
        write_line(
            f"{row['category']}: ${row['revenue']:,.2f}"
        )

    # Revenue by region
    region_data = (
        filtered.groupby("region", as_index=False)
        .agg(revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
    )

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    write_line("Revenue by Region", 9)

    pdf.set_font("Helvetica", size=10)

    for _, row in region_data.iterrows():
        write_line(
            f"{row['region']}: ${row['revenue']:,.2f}"
        )

    # Disclaimer
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)

    write_line(
        "Note: This report uses illustrative sample data for portfolio "
        "demonstration, not verified company results. CAC is marketing "
        "spend divided by new customers. AOV is revenue divided by orders. "
        "Churn is calculated using customer losses divided by starting "
        "customers in the selected records. This is a simplified "
        "demonstration calculation."
    )

    # Convert the PDF to downloadable bytes.
    # dest='S' supports FPDF versions that return a string or byte data.
    pdf_output = pdf.output(dest="S")

    if isinstance(pdf_output, str):
        return pdf_output.encode("latin-1")

    return bytes(pdf_output)


# --------------------------------------------------
# PDF DOWNLOAD BUTTON
# --------------------------------------------------
try:
    pdf_bytes = create_pdf()

    st.download_button(
        label="📄 Download Dashboard Report (PDF)",
        data=pdf_bytes,
        file_name="dashboard_report.pdf",
        mime="application/pdf",
        key="dashboard_pdf_download"
    )

except Exception as error:
    st.error(f"PDF generation failed: {error}")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.caption(
    "Portfolio demonstration | Illustrative sample data | "
    "Built with Python, Streamlit and Plotly"
)
