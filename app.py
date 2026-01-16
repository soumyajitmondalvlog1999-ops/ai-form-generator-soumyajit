import streamlit as st
import json
import hashlib

# Page configuration
st.set_page_config(
    page_title="AI Form Generator",
    page_icon="✨",
    layout="wide"
)

# Initialize session state
if 'current_form' not in st.session_state:
    st.session_state.current_form = None
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}
if 'user_prompt' not in st.session_state:
    st.session_state.user_prompt = ""

# Predefined form templates
FORM_TEMPLATES = {
    "doctor": {
        "title": "Doctors' Conference Registration",
        "description": "Register for the Annual Medical Conference",
        "fields": [
            {"name": "name", "label": "Full Name", "type": "text", "required": True, "placeholder": "Enter your full name"},
            {"name": "license", "label": "Medical License Number", "type": "text", "required": True, "placeholder": "Enter your medical license number"},
            {"name": "specialization", "label": "Specialization", "type": "select", "required": True, 
             "options": ["Cardiology", "Neurology", "Pediatrics", "Surgery", "Internal Medicine", "Other"]},
            {"name": "dietary", "label": "Dietary Restrictions", "type": "multiselect", "required": False,
             "options": ["Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Nut Allergy", "None"]},
            {"name": "email", "label": "Email Address", "type": "email", "required": True, "placeholder": "Enter your email"},
            {"name": "phone", "label": "Phone Number", "type": "tel", "required": False, "placeholder": "Enter your phone number"}
        ]
    },
    "fintech": {
        "title": "Fintech Conference Registration",
        "description": "Register for the Fintech Innovation Summit",
        "fields": [
            {"name": "name", "label": "Full Name", "type": "text", "required": True, "placeholder": "Enter your full name"},
            {"name": "mobile", "label": "Mobile Number", "type": "tel", "required": True, "placeholder": "Enter your mobile number"},
            {"name": "email", "label": "Email Address", "type": "email", "required": True, "placeholder": "Enter your email"},
            {"name": "company", "label": "Company/Organization", "type": "text", "required": True, "placeholder": "Enter your company name"},
            {"name": "job_title", "label": "Job Title", "type": "text", "required": True, "placeholder": "Enter your job title"},
            {"name": "pain_points", "label": "Business Pain Points", "type": "textarea", "required": False, "placeholder": "Describe your current business challenges..."},
            {"name": "interests", "label": "Topics of Interest", "type": "multiselect", "required": False, 
             "options": ["Blockchain", "Digital Payments", "AI in Finance", "RegTech", "WealthTech", "InsurTech"]}
        ]
    },
    "contact": {
        "title": "Contact Form",
        "description": "Get in touch with us",
        "fields": [
            {"name": "name", "label": "Full Name", "type": "text", "required": True, "placeholder": "Enter your full name"},
            {"name": "email", "label": "Email Address", "type": "email", "required": True, "placeholder": "Enter your email"},
            {"name": "subject", "label": "Subject", "type": "text", "required": True, "placeholder": "Enter subject"},
            {"name": "message", "label": "Message", "type": "textarea", "required": True, "placeholder": "Enter your message"}
        ]
    }
}

def get_form_template(prompt):
    """Select form template based on prompt keywords"""
    prompt_lower = prompt.lower()
    
    if any(word in prompt_lower for word in ["doctor", "medical", "license"]):
        return FORM_TEMPLATES["doctor"]
    elif any(word in prompt_lower for word in ["fintech", "business", "mobile"]):
        return FORM_TEMPLATES["fintech"]
    else:
        return FORM_TEMPLATES["contact"]

def render_form(form_spec):
    """Render a form based on specification"""
    st.markdown(f"## {form_spec['title']}")
    if form_spec.get('description'):
        st.markdown(form_spec['description'])
    
    st.divider()
    
    # Create a unique form ID
    form_id = f"form_{hashlib.md5(json.dumps(form_spec).encode()).hexdigest()[:8]}"
    
    # Create the form
    with st.form(key=form_id):
        form_values = {}
        
        for field in form_spec['fields']:
            field_name = field['name']
            field_label = field['label'] + (" *" if field.get('required', False) else "")
            field_type = field['type']
            placeholder = field.get('placeholder', "")
            options = field.get('options', [])
            
            # Create unique key for each field
            field_key = f"{form_id}_{field_name}"
            
            if field_type == "text":
                value = st.text_input(field_label, placeholder=placeholder, key=field_key)
                form_values[field_name] = value
                
            elif field_type == "email":
                value = st.text_input(field_label, placeholder=placeholder, key=field_key)
                form_values[field_name] = value
                
            elif field_type == "tel":
                value = st.text_input(field_label, placeholder=placeholder, key=field_key)
                form_values[field_name] = value
                
            elif field_type == "textarea":
                value = st.text_area(field_label, placeholder=placeholder, height=100, key=field_key)
                form_values[field_name] = value
                
            elif field_type == "select":
                value = st.selectbox(field_label, options=options, key=field_key)
                form_values[field_name] = value
                
            elif field_type == "multiselect":
                value = st.multiselect(field_label, options=options, key=field_key)
                form_values[field_name] = value
        
        # CRITICAL: Submit button MUST be inside the form
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("✅ Submit Form", use_container_width=True, type="primary")
    
    # Handle form submission
    if submitted:
        st.session_state.form_data = form_values
        st.session_state.form_submitted = True
        st.session_state.current_form_spec = form_spec
        st.rerun()
    
    return form_values, submitted

def display_results(form_data, form_spec):
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
            value = form_data.get(field_name, "")
            if isinstance(value, list):
                value = ", ".join(value) if value else "Not selected"
            elif not value:
                value = "Not provided"
            st.write(f"**{field_label}:** {value}")
    
    with col2:
        st.markdown("#### JSON Output")
        output = {
            "form_title": form_spec['title'],
            "submitted_data": form_data,
            "fields": [
                {
                    "name": field['name'],
                    "label": field['label'],
                    "type": field['type']
                } for field in form_spec['fields']
            ]
        }
        st.code(json.dumps(output, indent=2), language="json")
        
        # Download button
        json_str = json.dumps(output, indent=2)
        st.download_button(
            label="📥 Download as JSON",
            data=json_str,
            file_name="form_submission.json",
            mime="application/json",
            key=f"download_{hashlib.md5(json_str.encode()).hexdigest()[:8]}"
        )

# Custom CSS
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.main-container {
    background: white;
    border-radius: 20px;
    padding: 2rem;
    margin: 1rem;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.main-header {
    font-size: 2.5rem;
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
}

.form-section {
    background: #f8fafc;
    padding: 2rem;
    border-radius: 15px;
    border: 1px solid #e2e8f0;
    margin: 1rem 0;
}

/* Ensure submit button is visible */
.stFormSubmitButton button {
    background: linear-gradient(90deg, #667eea, #764ba2) !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
    padding: 0.75rem 2rem !important;
    border-radius: 10px !important;
    margin-top: 1rem !important;
}

.stButton button {
    background: linear-gradient(90deg, #667eea, #764ba2);
    color: white;
    border: none;
    font-weight: 600;
    padding: 0.75rem 2rem;
    border-radius: 10px;
}

.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

/* Input styling */
.stTextInput input, .stTextArea textarea {
    border-radius: 8px;
    border: 2px solid #e2e8f0;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}
</style>
""", unsafe_allow_html=True)

# Main app
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">✨ AI Form Generator</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Describe any form in plain English and see it appear instantly!</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 📝 Quick Examples")
    
    examples = [
        "Doctor conference registration form",
        "Fintech conference with business pain points",
        "Simple contact form",
        "Event registration form",
        "Job application form"
    ]
    
    for i, example in enumerate(examples):
        if st.button(f"📋 {example}", key=f"ex_{i}", use_container_width=True):
            st.session_state.user_prompt = example
            st.session_state.current_form = get_form_template(example)
            st.session_state.form_submitted = False
            st.rerun()
    
    st.divider()
    st.markdown("### ℹ️ How to use:")
    st.markdown("""
    1. Describe your form needs
    2. Click Generate Form
    3. Fill out the form
    4. Submit and view data
    5. Download as JSON
    """)

# Main content area
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    # User input
    user_prompt = st.text_area(
        "**Describe the form you need:**",
        placeholder="Example: 'I need a registration form for a doctors conference with name, medical license, and dietary restrictions'",
        height=120,
        value=st.session_state.user_prompt,
        key="prompt_input"
    )
    
    # Generate button
    if st.button("🚀 Generate Form", type="primary", use_container_width=True):
        if user_prompt.strip():
            with st.spinner("Creating your form..."):
                form_template = get_form_template(user_prompt)
                st.session_state.current_form = form_template
                st.session_state.form_submitted = False
                st.session_state.user_prompt = user_prompt
                st.rerun()
        else:
            st.warning("Please describe what form you need.")

# Display form if generated
if st.session_state.current_form and not st.session_state.form_submitted:
    st.divider()
    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    
    # Render the form - submit button will be inside this
    form_data, submitted = render_form(st.session_state.current_form)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Display results if form was submitted
if st.session_state.form_submitted and hasattr(st.session_state, 'current_form_spec'):
    st.divider()
    display_results(st.session_state.form_data, st.session_state.current_form_spec)
    
    # Reset button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Create New Form", type="secondary", use_container_width=True):
            st.session_state.current_form = None
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
    <p>✨ <b>AI Form Generator</b> | Instant Form Creation from Natural Language</p>
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
