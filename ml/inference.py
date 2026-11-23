"""
Inference engine and Water Quality Index (WQI) calculator with expert diagnostic advisor.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

class WaterQualityInferenceEngine:
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            model_dir = os.path.join(base_dir, 'ml', 'models')
            
        self.model_path = os.path.join(model_dir, 'potability_classifier.joblib')
        self.metadata_path = os.path.join(model_dir, 'model_metadata.json')
        
        if not os.path.exists(self.model_path) or not os.path.exists(self.metadata_path):
            from ml.train import train_and_export_models
            train_and_export_models()
            
        self.model = joblib.load(self.model_path)
        with open(self.metadata_path, 'r') as f:
            self.metadata = json.load(f)
            
        self.features = self.metadata['features']
        self.thresholds = self.metadata['standard_thresholds']
        
    def calculate_wqi(self, ph: float, turbidity: float, tds: float, 
                      temperature: float, dissolved_oxygen: float, conductivity: float) -> dict:
        """
        Calculates Water Quality Index (WQI) using weighted arithmetic index method.
        Returns numerical score (0-100), rating, color code, and description.
        """
        # Sub-indices (0 to 100 scale where 100 is best quality)
        q_ph = 100.0 * (1.0 - abs(ph - 7.0) / 3.0)
        q_turb = 100.0 * (1.0 - (turbidity / 15.0))
        q_tds = 100.0 * (1.0 - (tds / 1200.0))
        q_do = 100.0 * (dissolved_oxygen / 10.0)
        q_cond = 100.0 * (1.0 - (conductivity / 2000.0))
        
        q_ph = max(0.0, min(100.0, q_ph))
        q_turb = max(0.0, min(100.0, q_turb))
        q_tds = max(0.0, min(100.0, q_tds))
        q_do = max(0.0, min(100.0, q_do))
        q_cond = max(0.0, min(100.0, q_cond))
        
        # Unit weights
        wqi = (0.22 * q_ph + 0.20 * q_turb + 0.18 * q_tds + 0.22 * q_do + 0.18 * q_cond)
        wqi = round(max(0.0, min(100.0, float(wqi))), 2)
        
        if wqi >= 85:
            category = "Excellent"
            color = "#10B981"  # Emerald green
            status = "Safe for direct consumption & all domestic uses."
        elif wqi >= 70:
            category = "Good"
            color = "#3B82F6"  # Blue
            status = "Generally safe for consumption; minor conventional filtration recommended."
        elif wqi >= 50:
            category = "Poor"
            color = "#F59E0B"  # Amber
            status = "Unsuitable for drinking without intensive purification."
        elif wqi >= 35:
            category = "Very Poor"
            color = "#F97316"  # Orange
            status = "Highly contaminated; restricted to limited non-contact industrial uses."
        else:
            category = "Hazardous"
            color = "#EF4444"  # Red
            status = "Severe biological/chemical toxicity; completely unfit for human or animal contact."
            
        return {
            "wqi": wqi,
            "category": category,
            "color": color,
            "status": status,
            "sub_indices": {
                "ph_quality": round(q_ph, 1),
                "turbidity_quality": round(q_turb, 1),
                "tds_quality": round(q_tds, 1),
                "do_quality": round(q_do, 1),
                "conductivity_quality": round(q_cond, 1)
            }
        }
        
    def analyze_compliance_and_risks(self, data: dict) -> dict:
        """
        Compares sensor readings against EPA and WHO drinking water quality thresholds.
        Identifies parameter breaches, anomaly drivers, and purification recommendations.
        """
        breaches = []
        recommendations = []
        
        ph = data.get('ph', 7.0)
        turbidity = data.get('turbidity', 1.0)
        tds = data.get('tds', 200.0)
        temp = data.get('temperature', 20.0)
        do = data.get('dissolved_oxygen', 8.0)
        cond = data.get('conductivity', 350.0)
        
        # pH checks
        if ph < 6.5:
            breaches.append({
                "parameter": "pH",
                "value": ph,
                "limit": "6.5 - 8.5",
                "severity": "CRITICAL" if ph < 5.5 else "WARNING",
                "issue": "High Acidity: Corrosive, causes heavy metal leaching from pipes."
            })
            recommendations.append("Install Calcite or neutralizing filter / add alkaline buffer.")
        elif ph > 8.5:
            breaches.append({
                "parameter": "pH",
                "value": ph,
                "limit": "6.5 - 8.5",
                "severity": "CRITICAL" if ph > 9.2 else "WARNING",
                "issue": "High Alkalinity: Bitter taste, mineral encrustation, eye irritation."
            })
            recommendations.append("Apply mild organic acid dosing or cation-exchange water softening.")
            
        # Turbidity checks
        if turbidity > 5.0:
            breaches.append({
                "parameter": "Turbidity",
                "value": f"{turbidity:.1f} NTU",
                "limit": "< 5.0 NTU (EPA standard)",
                "severity": "CRITICAL" if turbidity > 10.0 else "WARNING",
                "issue": "Suspended particulate matter; high risk of harboring pathogens and cryptosporidium."
            })
            recommendations.append("Multi-stage sediment filtration (5µm / 1µm) + UV Disinfection unit.")
        elif turbidity > 1.0:
            breaches.append({
                "parameter": "Turbidity",
                "value": f"{turbidity:.1f} NTU",
                "limit": "< 1.0 NTU (Ideal WHO)",
                "severity": "INFO",
                "issue": "Acceptable for municipal, but exceeds WHO ideal clarity benchmark."
            })
            
        # TDS checks
        if tds > 500.0:
            breaches.append({
                "parameter": "TDS",
                "value": f"{tds:.0f} ppm",
                "limit": "< 500 ppm",
                "severity": "CRITICAL" if tds > 1000.0 else "WARNING",
                "issue": "Elevated Total Dissolved Solids; indicates excessive dissolved minerals, salts, or runoff."
            })
            recommendations.append("Reverse Osmosis (RO) system required to remove dissolved ions.")
            
        # Dissolved Oxygen checks
        if do < 5.0:
            breaches.append({
                "parameter": "Dissolved Oxygen",
                "value": f"{do:.2f} mg/L",
                "limit": "> 6.0 mg/L",
                "severity": "CRITICAL" if do < 3.0 else "WARNING",
                "issue": "Severe oxygen depletion (hypoxia); indicates stagnant water, anaerobic bacterial decomposition."
            })
            recommendations.append("Mechanical aeration / ozonation + activated carbon filtration.")
            
        # Conductivity checks
        if cond > 800.0:
            breaches.append({
                "parameter": "Conductivity",
                "value": f"{cond:.0f} µS/cm",
                "limit": "< 800 µS/cm",
                "severity": "CRITICAL" if cond > 1400.0 else "WARNING",
                "issue": "High electrical conductivity; indicates ionic contamination or industrial effluent."
            })
            if "Reverse Osmosis (RO) system required to remove dissolved ions." not in recommendations:
                recommendations.append("Deionization or Reverse Osmosis (RO) treatment.")
                
        # Temperature checks
        if temp > 28.0:
            breaches.append({
                "parameter": "Temperature",
                "value": f"{temp:.1f} °C",
                "limit": "< 25.0 °C",
                "severity": "INFO",
                "issue": "Elevated thermal conditions accelerate microbial proliferation and biofilm growth."
            })
            
        if not recommendations:
            recommendations.append("Water meets all EPA/WHO standards. Standard 1-stage carbon block filter is sufficient.")
            
        return {
            "breaches": breaches,
            "has_critical": any(b["severity"] == "CRITICAL" for b in breaches),
            "breach_count": len(breaches),
            "recommendations": recommendations
        }
        
    def predict(self, sensor_data: dict) -> dict:
        """
        Runs ML model potability classification, calculates WQI, and returns full diagnostics.
        """
        # Ensure all required features are present
        row = [
            float(sensor_data.get('ph', 7.0)),
            float(sensor_data.get('turbidity', 1.0)),
            float(sensor_data.get('tds', 200.0)),
            float(sensor_data.get('temperature', 20.0)),
            float(sensor_data.get('dissolved_oxygen', 8.0)),
            float(sensor_data.get('conductivity', 350.0))
        ]
        
        X_df = pd.DataFrame([row], columns=self.features)
        
        # Model prediction
        pred_label = int(self.model.predict(X_df)[0])
        pred_probs = self.model.predict_proba(X_df)[0]
        
        potability_confidence = float(pred_probs[pred_label])
        is_potable = bool(pred_label == 1)
        
        # Calculate WQI
        wqi_result = self.calculate_wqi(
            ph=row[0], turbidity=row[1], tds=row[2],
            temperature=row[3], dissolved_oxygen=row[4], conductivity=row[5]
        )
        
        # Compliance & Risks
        diagnostics = self.analyze_compliance_and_risks(sensor_data)
        
        # If there are severe critical breaches, potability should not be green
        if diagnostics["has_critical"] and is_potable:
            # Overwrite for strict safety compliance
            is_potable = False
            potability_confidence = 0.95
            
        return {
            "potability": "SAFE" if is_potable else "UNSAFE",
            "is_potable": is_potable,
            "confidence": round(potability_confidence * 100, 1),
            "probabilities": {
                "safe": round(float(pred_probs[1]) * 100, 1) if len(pred_probs) > 1 else 0.0,
                "unsafe": round(float(pred_probs[0]) * 100, 1) if len(pred_probs) > 1 else 0.0
            },
            "wqi": wqi_result,
            "diagnostics": diagnostics,
            "features": {
                "ph": row[0],
                "turbidity": row[1],
                "tds": row[2],
                "temperature": row[3],
                "dissolved_oxygen": row[4],
                "conductivity": row[5]
            }
        }

# Singleton instance
_engine = None

def get_inference_engine():
    global _engine
    if _engine is None:
        _engine = WaterQualityInferenceEngine()
    return _engine

if __name__ == '__main__':
    engine = get_inference_engine()
    sample_safe = {
        'ph': 7.3, 'turbidity': 1.2, 'tds': 210, 
        'temperature': 19.5, 'dissolved_oxygen': 8.2, 'conductivity': 320
    }
    sample_dirty = {
        'ph': 4.8, 'turbidity': 18.5, 'tds': 920, 
        'temperature': 27.0, 'dissolved_oxygen': 3.1, 'conductivity': 1450
    }
    print("Safe Water Test:")
    print(json.dumps(engine.predict(sample_safe), indent=2))
    print("\nContaminated Water Test:")
    print(json.dumps(engine.predict(sample_dirty), indent=2))
