# app/quotation.py
import joblib
import pandas as pd
import numpy as np
from .config import Config

class QuotePredictor:
    def __init__(self):
        self.model = joblib.load(f'{Config.MODEL_PATH}/quotation_model.pkl')
        self.encoders = joblib.load(f'{Config.MODEL_PATH}/quotation_encoders.pkl')
        self.scaler = joblib.load(f'{Config.MODEL_PATH}/scaler.pkl')
        self.features = ['vehicle_type_encoded', 'fuel_type_encoded', 'city_tier_encoded',
                        'make_encoded', 'manufacturing_year', 'idv', 'ncb_percent',
                        'vehicle_age', 'idv_age_ratio']
    
    def predict(self, data):
        """Predict premium for a vehicle"""
        df = pd.DataFrame([data])
        
        # Encode
        df['vehicle_type_encoded'] = self.encoders['vehicle_type'].transform(df['vehicle_type'])
        df['fuel_type_encoded'] = self.encoders['fuel_type'].transform(df['fuel_type'])
        df['city_tier_encoded'] = self.encoders['city_tier'].transform(df['city_tier'])
        df['make_encoded'] = self.encoders['make'].transform(df['vehicle_make'])
        
        # Feature engineering
        df['vehicle_age'] = 2024 - df['manufacturing_year']
        df['idv_age_ratio'] = df['idv'] / (df['vehicle_age'] + 1)
        
        # Scale and predict
        X = df[self.features]
        X_scaled = self.scaler.transform(X)
        premium = self.model.predict(X_scaled)[0]
        
        return round(premium, 2)