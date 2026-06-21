# app/main.py
import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

from .config import Config
from .database import get_session, save_quotation, save_claim, save_chat_log
from .rag_chatbot import PolicyChatbot
from .quotation import QuotePredictor
from .claims_engine import ClaimsEngine
from .dashboard import get_dashboard_data, create_kpi_cards, create_city_chart, create_trend_chart

# Page config
st.set_page_config(page_title="Acko Insurance AI Platform", page_icon="🛡️", layout="wide")

# Session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
    st.session_state.user_name = "Guest"
    st.session_state.user_role = "customer"
    st.session_state.authenticated = False

if 'chatbot' not in st.session_state:
    st.session_state.chatbot = PolicyChatbot()

if 'quote_predictor' not in st.session_state:
    st.session_state.quote_predictor = QuotePredictor()

if 'claims_engine' not in st.session_state:
    st.session_state.claims_engine = ClaimsEngine()

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.title("🛡️ Acko Insurance")
    st.markdown("---")
    
    # Auth
    if not st.session_state.authenticated:
        with st.form("auth"):
            name = st.text_input("Name", value="Guest User")
            email = st.text_input("Email", value="guest@example.com")
            role = st.selectbox("Role", ["customer", "manager"])
            if st.form_submit_button("Continue"):
                st.session_state.user_name = name
                st.session_state.user_role = role
                st.session_state.authenticated = True
                st.rerun()
    else:
        st.success(f"👋 {st.session_state.user_name}")
        st.info(f"Role: {st.session_state.user_role.title()}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
    
    st.markdown("---")
    
    # Navigation
    pages = ["💬 Policy Chatbot", "📊 Get Quote", "📸 File Claim"]
    if st.session_state.user_role == "manager":
        pages.extend(["📈 Dashboard", "🤖 Manager Assistant"])
    
    page = st.radio("Navigate", pages)

# ============================================================================
# PAGE 1: POLICY CHATBOT
# ============================================================================
if page == "💬 Policy Chatbot":
    st.title("💬 Acko Policy Assistant")
    st.caption("Ask any question about your insurance policy")
    
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Hello! I'm your Acko insurance assistant. Ask me anything about your policy!"}
        ]
    
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    if prompt := st.chat_input("Ask a policy question..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Searching policies..."):
                result = st.session_state.chatbot.query(prompt, st.session_state.user_id)
                st.markdown(result['answer'])
                if result['sources']:
                    st.caption(f"📚 Sources: {', '.join(set(result['sources']))}")
        
        st.session_state.chat_messages.append({"role": "assistant", "content": result['answer']})

# ============================================================================
# PAGE 2: GET QUOTE
# ============================================================================
elif page == "📊 Get Quote":
    st.title("📊 Instant Premium Quote")
    st.caption("Get an AI-powered premium estimate in seconds")
    
    with st.form("quote_form"):
        col1, col2 = st.columns(2)
        with col1:
            vehicle_type = st.selectbox("Vehicle Type", ["car", "bike"])
            make = st.selectbox("Make", ["Maruti", "Hyundai", "Honda", "Toyota", "Bajaj", "Hero", "TVS"])
            model = st.text_input("Model", "Swift")
            year = st.number_input("Manufacturing Year", 2010, 2024, 2020)
            fuel = st.selectbox("Fuel Type", ["Petrol", "Diesel", "Electric"])
        with col2:
            city = st.selectbox("City", ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune"])
            tier = st.selectbox("City Tier", ["tier1", "tier2", "tier3"])
            idv = st.number_input("Insured Declared Value (₹)", 50000, 1500000, 500000, step=10000)
            ncb = st.selectbox("No Claim Bonus (%)", [0, 20, 25, 35, 45, 50])
        
        if st.form_submit_button("Get Quote"):
            data = {
                'vehicle_type': vehicle_type,
                'vehicle_make': make,
                'vehicle_model': model,
                'manufacturing_year': year,
                'fuel_type': fuel,
                'city': city,
                'city_tier': tier,
                'idv': idv,
                'ncb_percent': ncb
            }
            premium = st.session_state.quote_predictor.predict(data)
            
            # Save
            data['user_id'] = st.session_state.user_id
            data['predicted_premium'] = premium
            save_quotation(get_session(), data)
            
            st.success(f"✅ Estimated Premium: ₹{premium:,.2f}")
            st.info(f"📌 Based on: IDV ₹{idv:,} | {ncb}% NCB | {year} {make} {model}")

# ============================================================================
# PAGE 3: FILE CLAIM
# ============================================================================
elif page == "📸 File Claim":
    st.title("📸 File a Claim")
    st.caption("Upload a photo of the damage for instant assessment")
    
    col1, col2 = st.columns(2)
    
    with col1:
        vehicle_type = st.selectbox("Vehicle Type", ["car", "bike"])
        policy = st.text_input("Policy Number", f"POL{datetime.now().strftime('%Y%m')}123")
        incident = st.date_input("Incident Date", datetime.now())
        
        # Manual override (for testing)
        with st.expander("Manual Damage Input (for testing)"):
            damage_type = st.selectbox("Damage Type", ["scratch", "dent", "crack", "major_damage", "total_loss"])
            severity = st.selectbox("Severity", ["minor", "moderate", "major"])
            parts = st.text_input("Damaged Parts", "bumper, door")
    
    with col2:
        st.subheader("Upload Damage Photo")
        image_file = st.file_uploader("Take or upload photo", type=["jpg", "png", "jpeg"])
        if image_file:
            st.image(image_file, caption="Damage Photo", use_column_width=True)
    
    if st.button("Submit Claim", type="primary"):
        if not image_file:
            st.warning("Please upload a damage photo")
        else:
            with st.spinner("Analyzing damage..."):
                claim_data = {
                    'vehicle_type': vehicle_type,
                    'policy_number': policy,
                    'incident_date': incident,
                    'image_bytes': image_file.getvalue(),
                    'damage_type': damage_type if 'damage_type' in locals() else 'dent',
                    'severity': severity if 'severity' in locals() else 'moderate',
                    'damaged_parts': parts.split(',') if 'parts' in locals() else ['bumper'],
                    'user_id': st.session_state.user_id
                }
                
                result = st.session_state.claims_engine.predict_claim(claim_data)
                
                # Save
                claim_data['predicted_amount'] = result['predicted_amount']
                claim_data['approval_probability'] = result['approval_probability']
                claim_data['status'] = result['status']
                save_claim(get_session(), claim_data)
                
                # Results
                col1, col2, col3 = st.columns(3)
                col1.metric("Estimated Payout", f"₹{result['predicted_amount']:,.2f}")
                col2.metric("Approval Probability", f"{result['approval_probability']*100:.1f}%")
                col3.metric("Status", result['status'].title())
                
                st.progress(result['approval_probability'])
                if result['approval_probability'] > 0.7:
                    st.success("✅ High chance of approval!")
                elif result['approval_probability'] > 0.4:
                    st.warning("⚠️ Moderate chance - may need review")
                else:
                    st.error("❌ Low chance of approval")

# ============================================================================
# PAGE 4: DASHBOARD
# ============================================================================
elif page == "📈 Dashboard":
    if st.session_state.user_role != "manager":
        st.warning("⚠️ Manager access required")
        st.stop()
    
    st.title("📈 Management Dashboard")
    
    stats, city_df, trend_df = get_dashboard_data()
    
    # KPI Cards
    cols = st.columns(4)
    for i, kpi in enumerate(create_kpi_cards(stats)):
        with cols[i]:
            st.metric(kpi['label'], kpi['value'], delta=kpi.get('delta'))
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        fig = create_city_chart(city_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No city data available")
    
    with col2:
        fig = create_trend_chart(trend_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trend data available")
    
    if st.button("🔄 Refresh"):
        st.rerun()

# ============================================================================
# PAGE 5: MANAGER ASSISTANT
# ============================================================================
elif page == "🤖 Manager Assistant":
    if st.session_state.user_role != "manager":
        st.warning("⚠️ Manager access required")
        st.stop()
    
    st.title("🤖 Manager AI Assistant")
    st.caption("Ask business questions in plain English")
    
    if "manager_msgs" not in st.session_state:
        st.session_state.manager_msgs = [
            {"role": "assistant", "content": "Hi! Ask me anything about your claims data. Example: 'How many car claims this month?'"}
        ]
    
    for msg in st.session_state.manager_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    if prompt := st.chat_input("Ask a business question..."):
        st.session_state.manager_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                # Use the RAG chatbot but with business context
                result = st.session_state.chatbot.query(prompt, st.session_state.user_id)
                
                # Add business stats context
                stats = get_dashboard_data()[0]
                context = f"\n\n📊 **Current Stats:**\n"
                context += f"- Total Claims: {stats['total_claims']}\n"
                context += f"- Approval Rate: {stats['approval_rate']:.1f}%\n"
                context += f"- Avg Claim: ₹{stats['avg_amount']:,.0f}\n"
                
                st.markdown(result['answer'] + context)
        
        st.session_state.manager_msgs.append({"role": "assistant", "content": result['answer']})

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.caption("🛡️ Acko Insurance AI Platform | 5-Module Architecture")