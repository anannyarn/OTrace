"""
ML Model Training & Calibration Pipeline for OTrace.
Trains Logistic Regression + Isotonic CalibratedClassifierCV.
Strictly splits train and test datasets by Person/Query ID to prevent data leakage.
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, brier_score_loss

from app.config import BASE_DIR, MODEL_PATH
from app.matching import FEATURE_NAMES
from eval.synthetic import generate_synthetic_dataset


def train_and_calibrate_model():
    """Trains calibrated identity resolution model."""
    dataset = generate_synthetic_dataset(num_persons=100)
    df = pd.DataFrame([
        {
            "person_id": item["person_id"],
            "label": item["is_same_person"],
            **item["features"]
        }
        for item in dataset
    ])

    # Group-based Train/Test Split by person_id
    person_ids = df["person_id"].unique()
    np.random.seed(42)
    np.random.shuffle(person_ids)

    split_idx = int(len(person_ids) * 0.7)
    train_ids = set(person_ids[:split_idx])
    test_ids = set(person_ids[split_idx:])

    train_df = df[df["person_id"].isin(train_ids)]
    test_df = df[df["person_id"].isin(test_ids)]

    X_train = train_df[FEATURE_NAMES].values
    y_train = train_df["label"].values

    X_test = test_df[FEATURE_NAMES].values
    y_test = test_df["label"].values

    # Base Classifier
    base_clf = LogisticRegression(C=1.0, max_iter=1000)
    base_clf.fit(X_train, y_train)

    # Calibrated Classifier (Isotonic)
    calibrated_clf = CalibratedClassifierCV(base_clf, method="isotonic", cv=5)
    calibrated_clf.fit(X_train, y_train)

    # Evaluate Test Predictions
    probs = calibrated_clf.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)

    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, zero_division=0)
    rec = recall_score(y_test, preds, zero_division=0)
    f1 = f1_score(y_test, preds, zero_division=0)
    brier = brier_score_loss(y_test, probs)

    print("=== OTrace Model Calibration & Training Results ===")
    print(f"Accuracy : {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall   : {rec:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"Brier Loss: {brier:.4f}")
    print("==================================================")

    # Ensure models directory exists
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(calibrated_clf, MODEL_PATH)
    print(f"Calibrated model successfully saved to {MODEL_PATH}")

    return calibrated_clf


if __name__ == "__main__":
    train_and_calibrate_model()
