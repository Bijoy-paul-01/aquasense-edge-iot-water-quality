"""
Dataset Generator for Water Quality and Potability.
Synthesizes physically realistic water sensor samples based on EPA and WHO standards.
Includes correlations between temperature, dissolved oxygen, TDS, conductivity, turbidity, and pH.
"""

import os
import numpy as np
import pandas as pd

def generate_water_dataset(n_samples: int = 6000, random_state: int = 42) -> pd.DataFrame:
    np.random.seed(random_state)
    
    # 50% Potable / Safe samples, 50% Non-Potable / Contaminated samples
    n_potable = n_samples // 2
    n_non_potable = n_samples - n_potable
    
    # ------------------ POTABLE WATER SAMPLES ------------------
    # Safe limits according to EPA / WHO:
    # pH: 6.5 - 8.5 (mean ~7.3)
    ph_potable = np.random.normal(loc=7.3, scale=0.45, size=n_potable)
    ph_potable = np.clip(ph_potable, 6.55, 8.45)
    
    # Temperature: 12 - 25 °C (mean ~18 °C)
    temp_potable = np.random.normal(loc=18.5, scale=3.5, size=n_potable)
    temp_potable = np.clip(temp_potable, 10.0, 26.0)
    
    # Turbidity: < 5.0 NTU (EPA safe threshold; mean ~1.8 NTU)
    turbidity_potable = np.random.gamma(shape=2.5, scale=0.8, size=n_potable)
    turbidity_potable = np.clip(turbidity_potable, 0.2, 4.8)
    
    # TDS: 100 - 450 ppm (EPA secondary limit is 500 ppm)
    tds_potable = np.random.normal(loc=240, scale=75, size=n_potable)
    tds_potable = np.clip(tds_potable, 60, 480)
    
    # Conductivity: closely correlated with TDS (Conductivity ≈ TDS / 0.65)
    cond_potable = (tds_potable / 0.65) + np.random.normal(0, 25, size=n_potable)
    cond_potable = np.clip(cond_potable, 90, 750)
    
    # Dissolved Oxygen: Healthy water has DO > 6.0 mg/L (theoretical saturation depends on temp)
    # Higher temp decreases DO solubility slightly
    do_potable = 11.5 - (0.18 * temp_potable) + np.random.normal(0, 0.4, size=n_potable)
    do_potable = np.clip(do_potable, 6.2, 12.0)
    
    potable_df = pd.DataFrame({
        'ph': ph_potable,
        'turbidity': turbidity_potable,
        'tds': tds_potable,
        'temperature': temp_potable,
        'dissolved_oxygen': do_potable,
        'conductivity': cond_potable,
        'potability': 1
    })
    
    # ------------------ NON-POTABLE WATER SAMPLES ------------------
    # Different contamination archetypes:
    # 1. Acidic Runoff / Acid Mine Drainage (low pH, high conductivity)
    # 2. Alkaline / Chemical Waste (high pH > 9.0, elevated TDS)
    # 3. Heavy Particulate / Microbial Runoff (high Turbidity > 5.0)
    # 4. Brackish / High Mineral Salinity (TDS > 500 - 2000 ppm)
    # 5. Eutrophic / Stagnant / Anoxic Water (DO < 5.0 mg/L, high temp, foul)
    
    archetypes = np.random.choice([
        'acidic', 'alkaline', 'turbid_runoff', 'high_salinity', 'anoxic_stagnant'
    ], size=n_non_potable, p=[0.20, 0.15, 0.25, 0.20, 0.20])
    
    ph_np = np.zeros(n_non_potable)
    turb_np = np.zeros(n_non_potable)
    tds_np = np.zeros(n_non_potable)
    temp_np = np.zeros(n_non_potable)
    do_np = np.zeros(n_non_potable)
    cond_np = np.zeros(n_non_potable)
    
    for i, arch in enumerate(archetypes):
        if arch == 'acidic':
            ph_np[i] = np.random.uniform(3.5, 6.3)
            turb_np[i] = np.random.uniform(2.0, 12.0)
            tds_np[i] = np.random.uniform(300, 950)
            temp_np[i] = np.random.uniform(14.0, 28.0)
            cond_np[i] = (tds_np[i] / 0.60) + np.random.uniform(50, 200)
            do_np[i] = np.random.uniform(3.5, 7.5)
            
        elif arch == 'alkaline':
            ph_np[i] = np.random.uniform(8.7, 11.5)
            turb_np[i] = np.random.uniform(2.5, 14.0)
            tds_np[i] = np.random.uniform(450, 1200)
            temp_np[i] = np.random.uniform(16.0, 32.0)
            cond_np[i] = (tds_np[i] / 0.55) + np.random.uniform(50, 250)
            do_np[i] = np.random.uniform(3.0, 6.8)
            
        elif arch == 'turbid_runoff':
            ph_np[i] = np.random.uniform(6.2, 8.8)
            turb_np[i] = np.random.uniform(5.5, 38.0)  # Extreme turbidity
            tds_np[i] = np.random.uniform(350, 1100)
            temp_np[i] = np.random.uniform(18.0, 34.0)
            cond_np[i] = (tds_np[i] / 0.65) + np.random.uniform(20, 150)
            do_np[i] = np.random.uniform(2.5, 5.8)
            
        elif arch == 'high_salinity':
            ph_np[i] = np.random.uniform(6.5, 8.6)
            turb_np[i] = np.random.uniform(1.0, 10.0)
            tds_np[i] = np.random.uniform(550, 2200)  # High dissolved solids
            temp_np[i] = np.random.uniform(15.0, 30.0)
            cond_np[i] = (tds_np[i] / 0.52) + np.random.uniform(100, 400)
            do_np[i] = np.random.uniform(4.0, 8.0)
            
        else: # anoxic_stagnant
            ph_np[i] = np.random.uniform(6.0, 7.9)
            turb_np[i] = np.random.uniform(4.0, 20.0)
            tds_np[i] = np.random.uniform(380, 850)
            temp_np[i] = np.random.uniform(24.0, 36.0) # warm stagnant
            cond_np[i] = (tds_np[i] / 0.65) + np.random.uniform(10, 100)
            do_np[i] = np.random.uniform(0.5, 4.2)  # Depleted oxygen
            
    non_potable_df = pd.DataFrame({
        'ph': ph_np,
        'turbidity': turb_np,
        'tds': tds_np,
        'temperature': temp_np,
        'dissolved_oxygen': do_np,
        'conductivity': cond_np,
        'potability': 0
    })
    
    df = pd.concat([potable_df, non_potable_df], ignore_index=True)
    df = df.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    
    # Calculate Water Quality Index (WQI) using weighted arithmetic index method:
    # Parameters standard values & weights:
    # pH: ideal 7.0, permissible 8.5, weight 0.22
    # Turbidity: ideal 0.0, permissible 5.0, weight 0.20
    # TDS: ideal 0.0, permissible 500.0, weight 0.18
    # DO: ideal 14.6, permissible 5.0, weight 0.22
    # Conductivity: ideal 0.0, permissible 1000.0, weight 0.18
    def compute_wqi(row):
        # Q_ph
        q_ph = 100.0 * (1.0 - abs(row['ph'] - 7.0) / 3.0)
        q_turb = 100.0 * (1.0 - (row['turbidity'] / 15.0))
        q_tds = 100.0 * (1.0 - (row['tds'] / 1200.0))
        q_do = 100.0 * (row['dissolved_oxygen'] / 10.0)
        q_cond = 100.0 * (1.0 - (row['conductivity'] / 2000.0))
        
        # Clip individual quality indices between 0 and 100
        q_ph = max(0.0, min(100.0, q_ph))
        q_turb = max(0.0, min(100.0, q_turb))
        q_tds = max(0.0, min(100.0, q_tds))
        q_do = max(0.0, min(100.0, q_do))
        q_cond = max(0.0, min(100.0, q_cond))
        
        wqi = (0.22 * q_ph + 0.20 * q_turb + 0.18 * q_tds + 0.22 * q_do + 0.18 * q_cond)
        return round(float(wqi), 2)
        
    df['wqi'] = df.apply(compute_wqi, axis=1)
    
    # Quality category based on WQI
    def get_wqi_category(score):
        if score >= 85:
            return 'Excellent'
        elif score >= 70:
            return 'Good'
        elif score >= 50:
            return 'Poor'
        elif score >= 35:
            return 'Very Poor'
        else:
            return 'Hazardous'
            
    df['wqi_category'] = df['wqi'].apply(get_wqi_category)
    return df

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    dataset_path = os.path.join(data_dir, 'water_quality_dataset.csv')
    df = generate_water_dataset(n_samples=6000)
    df.to_csv(dataset_path, index=False)
    print(f"Generated dataset with {len(df)} samples saved to: {dataset_path}")
    print(df.head())
    print("\nPotability balance:")
    print(df['potability'].value_counts())
    print("\nWQI Category distribution:")
    print(df['wqi_category'].value_counts())
