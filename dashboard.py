# app/dashboard.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from .database import get_session, get_dashboard_stats, Claim, Quotation

def get_dashboard_data():
    session = get_session()
    stats = get_dashboard_stats(session)
    
    # Claims by city
    from sqlalchemy import func
    city_data = session.query(Claim.city, func.count(Claim.id)).group_by(Claim.city).all()
    claims_by_city = pd.DataFrame(city_data, columns=['city', 'count']) if city_data else pd.DataFrame()
    
    # Claims trend
    trend_data = session.query(
        func.date(Claim.created_at).label('date'),
        func.count(Claim.id).label('count')
    ).group_by('date').order_by('date').all()
    claims_trend = pd.DataFrame(trend_data, columns=['date', 'count']) if trend_data else pd.DataFrame()
    
    return stats, claims_by_city, claims_trend

def create_kpi_cards(stats):
    return [
        {'label': 'Total Claims', 'value': stats['total_claims'], 'delta': f"{stats['car_claims']} cars, {stats['bike_claims']} bikes"},
        {'label': 'Avg Claim Amount', 'value': f"₹{stats['avg_amount']:,.0f}"},
        {'label': 'Approval Rate', 'value': f"{stats['approval_rate']:.1f}%"},
        {'label': 'Total Quotations', 'value': stats['total_quotations'], 'delta': f"Avg ₹{stats['avg_premium']:,.0f}"}
    ]

def create_city_chart(df):
    if df.empty:
        return None
    return px.bar(df, x='city', y='count', title='Claims by City', color='city')

def create_trend_chart(df):
    if df.empty:
        return None
    return px.line(df, x='date', y='count', title='Claims Trend', markers=True)