# app/claims_engine.py
import joblib
import numpy as np
import google.generativeai as genai
from .config import Config

class ClaimsEngine:
    def __init__(self):
        self.genai = Config.get_gemini_client()
        self.vision_model = self.genai.GenerativeModel('gemini-1.5-flash')
        
        # Load ML models
        self.models = {}
        self.scalers = {}
        for vehicle in ['car', 'bike']:
            self.models[f'{vehicle}_amount'] = joblib.load(f'{Config.MODEL_PATH}/{vehicle}_amount_model.pkl')
            self.models[f'{vehicle}_approval'] = joblib.load(f'{Config.MODEL_PATH}/{vehicle}_approval_model.pkl')
            self.scalers[f'{vehicle}_amount'] = joblib.load(f'{Config.MODEL_PATH}/{vehicle}_amount_scaler.pkl')
            self.scalers[f'{vehicle}_approval'] = joblib.load(f'{Config.MODEL_PATH}/{vehicle}_approval_scaler.pkl')
        
        self.encoders = joblib.load(f'{Config.MODEL_PATH}/claims_encoders.pkl')
    
    def analyze_damage_image(self, image_bytes):
        """Use Gemini Vision to analyze damage from photo"""
        prompt = """
        Analyze this vehicle damage photo and return JSON with:
        1. damage_type: scratch/dent/crack/major_damage/total_loss
        2. severity: minor/moderate/major
        3. damaged_parts: list of affected parts
        4. description: brief description of damage
        
        Return ONLY valid JSON.
        """
        response = self.vision_model.generate_content([prompt, image_bytes])
        import json
        try:
            return json.loads(response.text)
        except:
            return {'damage_type': 'dent', 'severity': 'moderate', 'damaged_parts': ['bumper']}
    
    def predict_claim(self, claim_data):
        """Predict claim amount and approval probability"""
        vehicle_type = claim_data.get('vehicle_type', 'car').lower()
        
        # If image provided, analyze it
        if 'image_bytes' in claim_data:
            vision_result = self.analyze_damage_image(claim_data['image_bytes'])
            claim_data.update(vision_result)
        
        # Prepare features
        damage_type = claim_data.get('damage_type', 'dent')
        severity = claim_data.get('severity', 'moderate')
        parts = claim_data.get('damaged_parts', ['bumper'])
        num_parts = len(parts)
        
        # Encode
        damage_encoded = self.encoders['damage_type'].transform([damage_type])[0]
        severity_encoded = self.encoders['severity'].transform([severity])[0]
        
        severity_score = {'minor': 1, 'moderate': 2, 'major': 3}[severity]
        complexity = {'scratch': 1, 'dent': 2, 'crack': 3, 'major_damage': 4, 'total_loss': 5}[damage_type]
        
        features = np.array([[
            damage_encoded, severity_encoded, num_parts, severity_score, complexity
        ]])
        
        # Predict
        amount_scaled = self.scalers[f'{vehicle_type}_amount'].transform(features)
        amount = self.models[f'{vehicle_type}_amount'].predict(amount_scaled)[0]
        
        approval_scaled = self.scalers[f'{vehicle_type}_approval'].transform(features)
        approval_prob = self.models[f'{vehicle_type}_approval'].predict_proba(approval_scaled)[0][1]
        
        status = 'approved' if approval_prob > Config.APPROVAL_THRESHOLD else 'review'
        if approval_prob < 0.3:
            status = 'rejected'
        
        return {
            'predicted_amount': float(amount),
            'approval_probability': float(approval_prob),
            'status': status,
            'damage_type': damage_type,
            'severity': severity
        }