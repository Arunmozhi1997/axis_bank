from fastapi import FastAPI
import pandas as pd
import joblib
from sqlalchemy import create_engine, text
import uuid
from datetime import datetime
import os

app = FastAPI()

# ==============================
# LOAD MODEL
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(BASE_DIR, "models", "trained_model.pkl")

model = joblib.load(model_path)

# ==============================
# DATABASE CONNECTION
# ==============================
DB_URL = os.getenv("DB_URL") or "postgresql://postgres:Kovilvenni@localhost:5432/axis_bank_ml"

engine = create_engine(DB_URL)

# ==============================
# FEATURE COLUMNS
# ==============================
feature_columns = [
    "avg_monthly_balance",
    "monthly_spend",
    "debit_credit_ratio",
    "emi_spend_ratio",
    "cash_withdrawal_ratio",
    "risk_score"
]

# ==============================
# HOME API
# ==============================
@app.get("/")
def home():
    return {"message": "Axis Bank Recommendation API Running 🚀"}

# ==============================
# RECOMMENDATION API (TOP-3)
# ==============================
@app.get("/recommend/{customer_id}")
def recommend(customer_id: str):

    try:
        # -----------------------------
        # FETCH CUSTOMER DATA
        # -----------------------------
        query = text("""
            SELECT * FROM feature_store 
            WHERE customer_id = :customer_id
        """)

        df = pd.read_sql(query, engine, params={"customer_id": customer_id})

        if df.empty:
            return {"error": "Customer not found"}

        # -----------------------------
        # PREPARE FEATURES
        # -----------------------------
        X = df[feature_columns].fillna(0)

        # -----------------------------
        # MODEL PREDICTION (TOP-3)
        # -----------------------------
        probs = model.predict_proba(X)[0]
        top3_idx = probs.argsort()[-3:][::-1]

        recommendations = []

        # -----------------------------
        # DB TRANSACTION
        # -----------------------------
        with engine.begin() as conn:

            for rank, idx in enumerate(top3_idx, start=1):

                product_id = int(model.classes_[idx])
                score = float(probs[idx])

                # ✅ FETCH PRODUCT NAME FROM DB
                product_df = pd.read_sql(
                    text("""
                        SELECT product_name 
                        FROM product_catalog 
                        WHERE product_id = :pid
                    """),
                    engine,
                    params={"pid": product_id}
                )

                product_name = (
                    product_df["product_name"].values[0]
                    if not product_df.empty else "Unknown"
                )

                # ✅ INSERT INTO DB
                conn.execute(
                    text("""
                        INSERT INTO recommendations 
                        (recommendation_id, customer_id, product_id, 
                         recommendation_score, recommendation_rank, recommendation_date)
                        VALUES (:id, :customer_id, :product_id, 
                                :score, :rank, :date)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "customer_id": customer_id,
                        "product_id": product_id,
                        "score": score,
                        "rank": rank,
                        "date": datetime.now()
                    }
                )

                # ✅ APPEND RESPONSE
                recommendations.append({
                    "rank": rank,
                    "product_id": product_id,
                    "product_name": product_name,
                    "confidence_score": round(score, 3)
                })

        # -----------------------------
        # FINAL RESPONSE
        # -----------------------------
        return {
            "customer_id": customer_id,
            "recommendations": recommendations
        }

    except Exception as e:
        return {"error": str(e)}

# ==============================
# PRODUCT INFO API
# ==============================
@app.get("/product/{product_id}")
def get_product(product_id: int):

    try:
        product_df = pd.read_sql(
            text("""
                SELECT product_name 
                FROM product_catalog 
                WHERE product_id = :pid
            """),
            engine,
            params={"pid": product_id}
        )

        if product_df.empty:
            return {"error": "Product not found"}

        return {
            "product_id": product_id,
            "product_name": product_df["product_name"].values[0]
        }

    except Exception as e:
        return {"error": str(e)}
