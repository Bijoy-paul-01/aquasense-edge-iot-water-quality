"""
Machine Learning Training Pipeline for Water Quality and Potability Detection.
Trains, evaluates, and exports the model pipeline and artifacts.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

def train_and_export_models():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_path = os.path.join(base_dir, 'data', 'water_quality_dataset.csv')
    model_dir = os.path.join(base_dir, 'ml', 'models')
    os.makedirs(model_dir, exist_ok=True)
    
    if not os.path.exists(data_path):
        from ml.dataset_generator import generate_water_dataset
        df = generate_water_dataset(n_samples=6000)
        df.to_csv(data_path, index=False)
    else:
        df = pd.read_csv(data_path)
        
    features = ['ph', 'turbidity', 'tds', 'temperature', 'dissolved_oxygen', 'conductivity']
    target = 'potability'
    
    X = df[features]
    y = df[target]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {
        'RandomForest': RandomForestClassifier(
            n_estimators=150, max_depth=12, random_state=42, n_jobs=-1
        ),
        'GradientBoosting': GradientBoostingClassifier(
            n_estimators=120, learning_rate=0.1, max_depth=5, random_state=42
        ),
        'LogisticRegression': LogisticRegression(
            max_iter=1000, random_state=42
        )
    }
    
    best_model_name = None
    best_f1 = -1.0
    best_model = None
    evaluation_results = {}
    
    print("=" * 60)
    print("Evaluating Machine Learning Models for Water Potability Detection")
    print("=" * 60)
    
    for name, model in models.items():
        if name == 'LogisticRegression':
            model.fit(X_train_scaled, y_train)
            preds = model.predict(X_test_scaled)
            probs = model.predict_proba(X_test_scaled)[:, 1]
        else:
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            probs = model.predict_proba(X_test)[:, 1]
            
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds)
        rec = recall_score(y_test, preds)
        f1 = f1_score(y_test, preds)
        auc = roc_auc_score(y_test, probs)
        cm = confusion_matrix(y_test, preds).tolist()
        
        evaluation_results[name] = {
            'accuracy': round(float(acc), 4),
            'precision': round(float(prec), 4),
            'recall': round(float(rec), 4),
            'f1_score': round(float(f1), 4),
            'roc_auc': round(float(auc), 4),
            'confusion_matrix': cm
        }
        
        print(f"[{name}] Acc: {acc:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} | F1: {f1:.4f} | AUC: {auc:.4f}")
        
        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name
            best_model = model
            
    print("-" * 60)
    print(f"Best Performing Model: {best_model_name} (F1-Score: {best_f1:.4f})")
    
    # Feature importance
    if hasattr(best_model, 'feature_importances_'):
        importances = best_model.feature_importances_
        feature_importance_dict = {
            feat: round(float(imp), 4) for feat, imp in zip(features, importances)
        }
        # Sort by importance descending
        feature_importance_dict = dict(sorted(feature_importance_dict.items(), key=lambda item: item[1], reverse=True))
    else:
        feature_importance_dict = {feat: 1.0 / len(features) for feat in features}
        
    print("\nFeature Importances:")
    for feat, imp in feature_importance_dict.items():
        print(f"  - {feat:18s}: {imp * 100:.2f}%")
        
    # Save best model and artifacts
    model_save_path = os.path.join(model_dir, 'potability_classifier.joblib')
    scaler_save_path = os.path.join(model_dir, 'scaler.joblib')
    metadata_save_path = os.path.join(model_dir, 'model_metadata.json')
    
    joblib.dump(best_model, model_save_path)
    joblib.dump(scaler, scaler_save_path)
    
    metadata = {
        'model_name': best_model_name,
        'features': features,
        'metrics': evaluation_results[best_model_name],
        'all_models_benchmark': evaluation_results,
        'feature_importance': feature_importance_dict,
        'standard_thresholds': {
            'ph': {'min_safe': 6.5, 'max_safe': 8.5, 'unit': 'pH', 'ideal': 7.2},
            'turbidity': {'min_safe': 0.0, 'max_safe': 5.0, 'unit': 'NTU', 'ideal': 1.0},
            'tds': {'min_safe': 50.0, 'max_safe': 500.0, 'unit': 'ppm', 'ideal': 200.0},
            'temperature': {'min_safe': 10.0, 'max_safe': 25.0, 'unit': '°C', 'ideal': 18.0},
            'dissolved_oxygen': {'min_safe': 6.0, 'max_safe': 14.0, 'unit': 'mg/L', 'ideal': 8.5},
            'conductivity': {'min_safe': 100.0, 'max_safe': 800.0, 'unit': 'µS/cm', 'ideal': 350.0}
        }
    }
    
    with open(metadata_save_path, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    print("\nArtifacts successfully saved to:")
    print(f"  Model:    {model_save_path}")
    print(f"  Scaler:   {scaler_save_path}")
    print(f"  Metadata: {metadata_save_path}")
    print("=" * 60)
    return metadata

if __name__ == '__main__':
    train_and_export_models()
