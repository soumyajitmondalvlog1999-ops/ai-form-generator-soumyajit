import streamlit as st
import json
import re
import os
from openai import OpenAI
from dotenv import load_dotenv
import hashlib

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Form Generator",
    page_icon="✨",
    layout="wide"
)

# Initialize session state
if 'generated_form' not in st.session_state:
    st.session_state.generated_form = None
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}
if 'user_prompt' not in st.session_state:
    st.session_state.user_prompt = ""
if 'use_ai' not in st.session_state:
    st.session_state.use_ai = True

# Sample forms
DOCTOR_FORM = {
    "title": "Doctors' Conference Registration",
    "description": "Register for the Annual Medical Conference",
    "fields": [
        {"name": "name", "label": "Full Name", "type": "text", "required": True},
        {"name": "license", "label": "Medical License Number", "type": "text", "required": True},
        {"name": "specialization", "label": "Specialization", "type": "select", "required": True, 
         "options": ["Cardiology", "Neurology", "Pediatrics", "Surgery", "Other"]},
        {"name": "dietary", "label": "Dietary Restrictions", "type": "multiselect", "required": False,
         "options": ["Vegetarian", "Vegan", "Gluten-Free", "None"]},
        {"name": "email", "label": "Email", "type": "email", "required": True},
        {"name": "phone", "label": "Phone", "type": "tel", "required": False}
    ]
}

FINTECH_FORM = {
    "title": "Fintech Conference Registration",
    "description": "Register for the Fintech Innovation Summit",
    "fields": [
        {"name": "name", "label": "Full Name", "type": "text", "required": True},
        {"name": "mobile", "label": "Mobile Number", "type": "tel", "required": True},
        {"name": "email", "label": "Email", "type": "email", "required": True},
        {"name": "company", "label": "Company", "type": "text", "required": True},
        {"name": "pain_points", "label": "Business Pain Points", "type": "textarea", "required": False}
    ]
}

def get_form_from_prompt(prompt):
    """Get form template based on prompt keywords"""
    prompt_lower = prompt.lower()
    
    if any(word in prompt_lower for word in ["doctor", "medical", "license"]):
        return DOCTOR_FORM
    elif any(word in prompt_lower for word in ["fintech", "business pain", "mobile"]):
        return FINTECH_FORM
    else:
        # Simple contact form as fallback
        return {
            "title": "Contact Form",
            "description": "Please fill out this contact form",
            "fields": [
                {"name": "name", "label": "Name", "type": "text", "required": True},
                {"name": "email", "label": "Email", "type": "email", "required": True},
                {"name": "message", "label": "Message", "type": "textarea", "required": False}
            ]
        }

def create_form(form_spec):
    """Create and display a form based on specification"""
    st.markdown(f"### {form_spec['title']}")
    if form_spec.get('description'):
        st.markdown(form_spec['description'])
    
    st.divider()
    
    # Create a unique form key
    form_key = f"form_{hashlib.md5(json.dumps(form_spec).encode()).hexdigest()[:8]}"
    
    # Initialize form data if not exists
    if form_key not in st.session_state:
        st.session_state[form_key] = {field['name']: "" for field in form_spec['fields']}
    
    # Create the form using st.form
    with st.form(key=form_key):
        form_values = {}
        
        for field in form_spec['fields']:
            field_name = field['name']
            field_label = field['label'] + (" *" if field.get('required', False) else "")
            field_type = field['type']
            field_options = field.get('options', [])
            
            # Get current value from session state
            current_value = st.session_state[form_key].get(field_name, "")
            
            if field_type == "text":
                value = st.text_input(field_label, value=current_value, key=f"{form_key}_{field_name}_text")
                form_values[field_name] = value
                
            elif field_type == "email":
                value = st.text_input(field_label, value=current_value, key=f"{form_key}_{field_name}_email")
                form_values[field_name] = value
                
            elif field_type == "tel":
                value = st.text_input(field_label, value=current_value, key=f"{form_key}_{field_name}_tel")
                form_values[field_name] = value
                
            elif field_type == "textarea":
                value = st.text_area(field_label, value=current_value, height=100, key=f"{form_key}_{field_name}_textarea")
                form_values[field_name] = value
                
            elif field_type == "select":
                value = st.selectbox(
                    field_label, 
                    options=field_options,
                    index=0,
                    key=f"{form_key}_{field_name}_select"
                )
                form_values[field_name] = value
                
            elif field_type == "multiselect":
                value = st.multiselect(
                    field_label,
                    options=field_options,
                    key=f"{form_key}_{field_name}_multiselect"
                )
                form_values[field_name] = value
        
        # SUBMIT BUTTON - This is the critical part
        submitted = st.form_submit_button("✅ Submit Form", use_container_width=True)
    
    # Handle form submission
    if submitted:
        # Update session state
        st.session_state[form_key] = form_values
        st.session_state.form_data = form_values
        st.session_state.form_submitted = True
        st.session_state.current_form_spec = form_spec
        
        # Force a rerun to show results
        st.rerun()
    
    return form_values, submitted

def show_results(form_data, form_spec):
    """Display submitted form data"""
    st.success("✅ Form submitted successfully!")
    st.divider()
    
    st.markdown("### 📋 Submitted Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Form Values")
        for field in form_spec['fields']:
            field_name = field['name']
            field_label = field['label']
            value = form_data.get(field_name, "Not provided")
            if isinstance(value, list):
                value = ", ".join(value) if value else "None selected"
            st.write(f"**{field_label}:** {value}")
    
    with col2:
        st.markdown("#### JSON Output")
        output = {
            "form_title": form_spec['title'],
            "submitted_data": form_data
        }
        st.code(json.dumps(output, indent=2), language="json")
        
        # Download button
        json_str = json.dumps(output, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name="form_data.json",
            mime="application/json"
        )

# Custom CSS for styling
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    background-attachment: fixed;
}

.main-container {
    background: white;
    border-radius: 20px;
    padding: 2rem;
    margin: 1rem;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.main-header {
    font-size: 3rem;
    background: linear-gradient(90deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 1rem;
}

.sub-header {
    color: #6b7280;
    text-align: center;
    margin-bottom: 2rem;
    font-size: 1.2rem;
}

.form-container {
    background: #f9fafb;
    padding: 2rem;
    border-radius: 15px;
    border: 1px solid #e5e7eb;
    margin: 1rem 0;
}

.stButton button {
    background: linear-gradient(90deg, #667eea, #764ba2);
    color: white;
    font-weight: 600;
    border: none;
    padding: 0.75rem 2rem;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.3s ease;
    width: 100%;
}

.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
}
</style>
""", unsafe_allow_html=True)

# Main app layout
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">✨ AI Form Generator</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Describe the form you need in plain English, and watch it appear instantly!</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 📝 Examples")
    
    examples = [
        "I need a registration form for a doctors' conference",
        "Create a Fintech conference registration form",
        "Make a simple contact form"
    ]
    
    for i, example in enumerate(examples):
        if st.button(example, key=f"ex_{i}"):
            st.session_state.user_prompt = example
            st.session_state.generated_form = get_form_from_prompt(example)
            st.session_state.form_submitted = False
            st.rerun()
    
    st.divider()
    st.markdown("## ⚙️ Settings")
    st.session_state.use_ai = st.toggle("Use AI Features", value=True)

# Main content
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # Input for form description
    user_prompt = st.text_area(
        "**Describe your form:**",
        placeholder="Example: 'I need a registration form for a doctors' conference with name, license number, and dietary restrictions'",
        height=100,
        value=st.session_state.user_prompt,
        key="prompt_input"
    )
    
    # Generate button
    if st.button("🚀 Generate Form", type="primary", use_container_width=True):
        if user_prompt.strip():
            with st.spinner("Creating your form..."):
                form_spec = get_form_from_prompt(user_prompt)
                st.session_state.generated_form = form_spec
                st.session_state.form_submitted = False
                st.session_state.user_prompt = user_prompt
                st.rerun()
        else:
            st.warning("Please describe the form you need.")

# Display generated form
if st.session_state.generated_form and not st.session_state.form_submitted:
    st.divider()
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    
    # Create the form
    form_data, submitted = create_form(st.session_state.generated_form)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Display results if form was submitted
if st.session_state.form_submitted and hasattr(st.session_state, 'current_form_spec'):
    st.divider()
    show_results(st.session_state.form_data, st.session_state.current_form_spec)
    
    # Reset button
    if st.button("🔄 Create Another Form", type="secondary", use_container_width=True):
        st.session_state.generated_form = None
        st.session_state.form_submitted = False
        st.session_state.form_data = {}
        st.session_state.user_prompt = ""
        if hasattr(st.session_state, 'current_form_spec'):
            del st.session_state.current_form_spec
        st.rerun()

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #6B7280; padding: 1rem;">
    <p>✨ AI Form Generator | Built with Streamlit</p>
    <p><small>Simply describe, generate, and collect!</small></p>
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
