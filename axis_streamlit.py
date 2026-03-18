import streamlit as st
import pandas as pd
import requests
from sqlalchemy import create_engine, text

# ==============================
# DATABASE CONNECTION
# ==============================
username = "postgres"
password = "Kovilvenni"
host = "localhost"
port = "5432"
database = "axis_bank_ml"

engine = create_engine(
    f"postgresql://{username}:{password}@{host}:{port}/{database}"
)

# ==============================
# STREAMLIT UI
# ==============================
st.set_page_config(page_title="Axis Bank Dashboard", layout="wide")

st.title("🏦 Axis Bank Recommendation Dashboard")

# ==============================
# INPUT CUSTOMER ID
# ==============================
customer_id = st.text_input("Enter Customer ID", "CIF00000001")

# ==============================
# BUTTON
# ==============================
if st.button("Get Recommendation"):

    url = f"http://127.0.0.1:8000/recommend/{customer_id}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        if "error" in data:
            st.error(data["error"])
        else:
            st.success("✅ Recommendation Generated")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Customer Info")
                st.write("Customer ID:", data["customer_id"])

            with col2:
                st.subheader("Top-3 Recommendations")

                recs = data["recommendations"]

                for rec in recs:
                    st.write(
                        f"Rank {rec['rank']} → {rec['product_name']} "
                        f"(Score: {rec['confidence_score']})"
                    )

                # Optional: Show as table
                df_recs = pd.DataFrame(recs)
                st.dataframe(df_recs)

    else:
        st.error("API Error")

# ==============================
# SHOW CUSTOMER FEATURES
# ==============================
st.subheader("📊 Customer Features")

query = text("""
SELECT * FROM feature_store
WHERE customer_id = :customer_id
""")

df_features = pd.read_sql(query, engine, params={"customer_id": customer_id})

if not df_features.empty:
    st.dataframe(df_features)
else:
    st.warning("No customer data found")

# ==============================
# SHOW PAST RECOMMENDATIONS
# ==============================
st.subheader("📜 Past Recommendations")

query2 = text("""
SELECT *
FROM recommendations
WHERE customer_id = :customer_id
ORDER BY recommendation_date DESC
""")

df_rec = pd.read_sql(query2, engine, params={"customer_id": customer_id})

if not df_rec.empty:
    st.dataframe(df_rec)
else:
    st.warning("No recommendations yet")

# ==============================
# ANALYTICS
# ==============================
st.subheader("📈 Analytics")

query3 = """
SELECT product_id, COUNT(*) as count
FROM recommendations
GROUP BY product_id
"""

df_analytics = pd.read_sql(query3, engine)

if not df_analytics.empty:
    st.bar_chart(df_analytics.set_index("product_id"))