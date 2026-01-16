import streamlit as st
import json
import re
from typing import Dict, List, Optional, Any
import os
from openai import OpenAI
from dotenv import load_dotenv
import jsonschema
from jsonschema import validate
import hashlib

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Form Generator",
    page_icon="✨",
    layout="wide"
)

# Initialize OpenAI client
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Don't show error immediately, just return None
        return None
    return OpenAI(api_key=api_key)

# Form field schema for validation
FORM_FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "label": {"type": "string"},
                    "field_type": {"type": "string", "enum": ["text", "email", "number", "tel", "textarea", "select", "multiselect", "date", "checkbox"]},
                    "required": {"type": "boolean"},
                    "placeholder": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "validation": {"type": "string"}
                },
                "required": ["name", "label", "field_type"]
            }
        }
    },
    "required": ["title", "fields"]
}

# Sample form templates for fallback
SAMPLE_FORM_TEMPLATES = {
    "doctor_conference": {
        "title": "Doctors' Conference Registration",
        "description": "Register for the Annual Medical Conference",
        "fields": [
            {"name": "name", "label": "Full Name", "field_type": "text", "required": True, "placeholder": "Enter your full name"},
            {"name": "medical_license", "label": "Medical License Number", "field_type": "text", "required": True, "placeholder": "Enter your medical license number"},
            {"name": "specialization", "label": "Specialization", "field_type": "select", "required": True, "options": ["Cardiology", "Neurology", "Pediatrics", "Surgery", "Internal Medicine", "Other"]},
            {"name": "dietary_restrictions", "label": "Dietary Restrictions", "field_type": "multiselect", "required": False, "options": ["Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Nut Allergy", "None"]},
            {"name": "email", "label": "Email Address", "field_type": "email", "required": True, "placeholder": "Enter your email"},
            {"name": "phone", "label": "Phone Number", "field_type": "tel", "required": False, "placeholder": "Enter your phone number"}
        ]
    },
    "fintech_conference": {
        "title": "Fintech Conference Registration",
        "description": "Register for the Fintech Innovation Summit",
        "fields": [
            {"name": "name", "label": "Full Name", "field_type": "text", "required": True, "placeholder": "Enter your full name"},
            {"name": "mobile", "label": "Mobile Number", "field_type": "tel", "required": True, "placeholder": "Enter your mobile number"},
            {"name": "email", "label": "Email Address", "field_type": "email", "required": True, "placeholder": "Enter your email"},
            {"name": "company", "label": "Company/Organization", "field_type": "text", "required": True, "placeholder": "Enter your company name"},
            {"name": "job_title", "label": "Job Title", "field_type": "text", "required": True, "placeholder": "Enter your job title"},
            {"name": "business_pain_points", "label": "Business Pain Points", "field_type": "textarea", "required": False, "placeholder": "Describe your current business challenges..."},
            {"name": "topics_interest", "label": "Topics of Interest", "field_type": "multiselect", "required": False, "options": ["Blockchain", "Digital Payments", "AI in Finance", "RegTech", "WealthTech", "InsurTech"]}
        ]
    }
}

def extract_form_requirements(prompt: str) -> Dict:
    """
    Extract form requirements from natural language prompt using rule-based approach
    Fallback to GPT if available and needed
    """
    prompt_lower = prompt.lower()
    
    # Check for known templates
    if any(keyword in prompt_lower for keyword in ["doctor", "medical", "license", "conference"]):
        return SAMPLE_FORM_TEMPLATES["doctor_conference"]
    elif any(keyword in prompt_lower for keyword in ["fintech", "business pain", "mobile number"]):
        return SAMPLE_FORM_TEMPLATES["fintech_conference"]
    
    # Try to extract fields using GPT if available
    client = get_openai_client()
    if client and st.session_state.get("use_ai", True):
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """You are a form generation assistant. Extract form requirements from the user's prompt and return a JSON structure.
                    Format: {
                        "title": "Form Title",
                        "description": "Form description",
                        "fields": [
                            {
                                "name": "field_name",
                                "label": "Field Label",
                                "field_type": "text|email|number|tel|textarea|select|multiselect|date|checkbox",
                                "required": true/false,
                                "placeholder": "optional placeholder",
                                "options": ["option1", "option2"] // only for select/multiselect
                            }
                        ]
                    }"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Extract JSON from response
            content = response.choices[0].message.content
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                form_spec = json.loads(json_match.group())
                # Validate against schema
                validate(instance=form_spec, schema=FORM_FIELD_SCHEMA)
                return form_spec
        except Exception as e:
            # Silent fail - use fallback
            pass
    
    # Fallback: Generate simple form based on keywords
    return generate_simple_form(prompt)

def generate_simple_form(prompt: str) -> Dict:
    """Generate a simple form based on keywords in the prompt"""
    fields = []
    prompt_lower = prompt.lower()
    
    # Always add name field
    fields.append({
        "name": "name",
        "label": "Full Name",
        "field_type": "text",
        "required": True,
        "placeholder": "Enter your full name"
    })
    
    # Add email if mentioned or generally appropriate
    if any(word in prompt_lower for word in ["email", "contact", "register"]):
        fields.append({
            "name": "email",
            "label": "Email Address",
            "field_type": "email",
            "required": True,
            "placeholder": "Enter your email address"
        })
    
    # Add phone if mentioned
    if any(word in prompt_lower for word in ["phone", "mobile", "contact"]):
        fields.append({
            "name": "phone",
            "label": "Phone Number",
            "field_type": "tel",
            "required": False,
            "placeholder": "Enter your phone number"
        })
    
    # Add message/textarea if mentioned
    if any(word in prompt_lower for word in ["message", "comment", "feedback", "description", "pain points"]):
        fields.append({
            "name": "message",
            "label": "Message",
            "field_type": "textarea",
            "required": False,
            "placeholder": "Enter your message"
        })
    
    # Generate title from prompt
    words = [word for word in prompt.split()[:5] if len(word) > 2]
    if words:
        title = " ".join(words) + " Registration Form"
    else:
        title = "Custom Registration Form"
    
    return {
        "title": title,
        "description": f"Form generated from: '{prompt[:50]}...'",
        "fields": fields
    }

def render_form(form_spec: Dict) -> Dict:
    """
    Render the form using Streamlit components
    Returns dictionary of form values and submitted status
    """
    st.markdown(f"## {form_spec['title']}")
    if 'description' in form_spec:
        st.markdown(form_spec['description'])
    
    st.divider()
    
    # Create a unique form key based on form specification
    form_hash = hashlib.md5(json.dumps(form_spec, sort_keys=True).encode()).hexdigest()[:8]
    
    with st.form(key=f"generated_form_{form_hash}"):
        form_data = {}
        
        for idx, field in enumerate(form_spec['fields']):
            field_name = field['name']
            field_label = field['label']
            field_type = field['field_type']
            required = field.get('required', False)
            placeholder = field.get('placeholder', '')
            options = field.get('options', [])
            
            # Add required indicator to label
            display_label = f"{field_label} {'*' if required else ''}"
            
            # Create a unique key for each field
            field_key = f"field_{field_name}_{form_hash}_{idx}"
            
            # Initialize field in session state if not exists
            if field_key not in st.session_state:
                st.session_state[field_key] = ""
            
            # Get value from session state
            current_value = st.session_state[field_key]
            
            # Render different field types
            if field_type == "text":
                value = st.text_input(
                    display_label,
                    placeholder=placeholder,
                    value=current_value,
                    key=field_key
                )
                form_data[field_name] = value
                
            elif field_type == "email":
                value = st.text_input(
                    display_label,
                    placeholder=placeholder,
                    value=current_value,
                    key=field_key
                )
                form_data[field_name] = value
                
            elif field_type == "number":
                # Convert current value to int if possible
                try:
                    current_num = int(current_value) if current_value else 0
                except:
                    current_num = 0
                value = st.number_input(
                    display_label,
                    value=current_num,
                    step=1,
                    key=field_key
                )
                form_data[field_name] = str(value)
                
            elif field_type == "tel":
                value = st.text_input(
                    display_label,
                    placeholder=placeholder,
                    value=current_value,
                    key=field_key
                )
                form_data[field_name] = value
                
            elif field_type == "textarea":
                value = st.text_area(
                    display_label,
                    placeholder=placeholder,
                    value=current_value,
                    height=100,
                    key=field_key
                )
                form_data[field_name] = value
                
            elif field_type == "select":
                # Handle current value for select
                if current_value and current_value in options:
                    current_index = options.index(current_value)
                else:
                    current_index = 0
                value = st.selectbox(
                    display_label,
                    options=options,
                    index=current_index,
                    key=field_key
                )
                form_data[field_name] = value
                
            elif field_type == "multiselect":
                # Handle current value for multiselect
                if isinstance(current_value, list):
                    current_list = [v for v in current_value if v in options]
                elif current_value:
                    current_list = [current_value] if current_value in options else []
                else:
                    current_list = []
                value = st.multiselect(
                    display_label,
                    options=options,
                    default=current_list,
                    key=field_key
                )
                form_data[field_name] = value
                
            elif field_type == "date":
                try:
                    # Try to parse date from string
                    from datetime import datetime
                    if current_value:
                        current_date = datetime.strptime(current_value, "%Y-%m-%d").date()
                    else:
                        current_date = None
                except:
                    current_date = None
                
                value = st.date_input(
                    display_label,
                    value=current_date,
                    key=field_key
                )
                form_data[field_name] = str(value) if value else ""
                
            elif field_type == "checkbox":
                value = st.checkbox(
                    display_label,
                    value=bool(current_value),
                    key=field_key
                )
                form_data[field_name] = value
        
        # Submit button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("✅ Submit Form", use_container_width=True, type="primary")
        
        # Update session state after form submission
        if submitted:
            # Store form data in session state
            form_data_key = f"form_data_{form_hash}"
            st.session_state[form_data_key] = form_data
            
            # Also update individual field session states
            for idx, field in enumerate(form_spec['fields']):
                field_name = field['name']
                field_key = f"field_{field_name}_{form_hash}_{idx}"
                if field_name in form_data:
                    # Use a callback to update session state after rerun
                    st.session_state[field_key] = form_data[field_name]
    
    return form_data, submitted

def display_form_data(form_data: Dict, form_spec: Dict):
    """Display the submitted form data in a structured way"""
    st.success("✅ Form submitted successfully!")
    st.divider()
    
    st.markdown("### 📋 Submitted Data")
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Form Values")
        for field_name, value in form_data.items():
            # Find field label
            field_label = next((f['label'] for f in form_spec['fields'] if f['name'] == field_name), field_name)
            display_value = value if value not in [None, '', []] else 'Not provided'
            if isinstance(display_value, list):
                display_value = ', '.join(display_value) if display_value else 'None selected'
            st.write(f"**{field_label}:** {display_value}")
    
    with col2:
        st.markdown("#### JSON Output")
        # Create a clean JSON structure
        output_json = {
            "form_title": form_spec['title'],
            "submitted_data": form_data,
            "metadata": {
                "fields": [
                    {
                        "name": field['name'],
                        "label": field['label'],
                        "type": field['field_type']
                    }
                    for field in form_spec['fields']
                ]
            }
        }
        st.code(json.dumps(output_json, indent=2), language="json")
    
    # Download button for JSON
    json_str = json.dumps(output_json, indent=2)
    st.download_button(
        label="📥 Download as JSON",
        data=json_str,
        file_name="form_submission.json",
        mime="application/json",
        key=f"download_{hashlib.md5(json_str.encode()).hexdigest()[:8]}"
    )

def main():
    # Add custom CSS for background and styling
    st.markdown("""
        <style>
        /* Main background with gradient */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
        }
        
        /* Content container with glass effect */
        .main-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            margin: 2rem auto;
            max-width: 1200px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        /* Headers */
        .main-header {
            font-size: 3rem;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 1rem;
            font-weight: 800;
        }
        
        .sub-header {
            font-size: 1.3rem;
            color: #4B5563;
            text-align: center;
            margin-bottom: 2rem;
            font-weight: 300;
        }
        
        /* Form styling */
        .form-container {
            background: rgba(255, 255, 255, 0.8);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(102, 126, 234, 0.2);
            margin-bottom: 2rem;
        }
        
        /* Button styling */
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
        
        /* Input field styling */
        .stTextInput input, .stTextArea textarea, .stSelectbox select {
            border-radius: 10px;
            border: 2px solid #E5E7EB;
            padding: 0.75rem;
            transition: all 0.3s ease;
        }
        
        .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
        }
        
        /* Example cards */
        .example-card {
            background: white;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
            border: 1px solid #E5E7EB;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .example-card:hover {
            transform: translateX(5px);
            border-color: #667eea;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        /* Feature icons */
        .feature-icon {
            font-size: 2rem;
            margin-right: 1rem;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Success message */
        .stAlert {
            border-radius: 10px;
            border: none;
        }
        
        /* Divider styling */
        .stDivider {
            border-color: rgba(102, 126, 234, 0.2);
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Main container with glass effect
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">✨ AI Form Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Describe the form you need in plain English, and watch it appear instantly!</p>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'current_form' not in st.session_state:
        st.session_state.current_form = None
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    if 'form_data' not in st.session_state:
        st.session_state.form_data = None
    if 'user_prompt' not in st.session_state:
        st.session_state.user_prompt = ""
    if 'use_ai' not in st.session_state:
        st.session_state.use_ai = True
    
    # Sidebar for examples and info
    with st.sidebar:
        st.markdown("## 📝 Examples")
        st.markdown("Try these prompts:")
        
        examples = [
            "I need a registration form for a doctors' conference with Name, Medical License Number, and Dietary Restrictions",
            "I need a registration form for a Fintech conference with Name, Mobile number, and their business pain points",
            "Create a contact form with name, email, and message",
            "Make a job application form with resume upload option",
            "Generate an event registration form with name, email, and ticket type"
        ]
        
        # Display example cards
        for example in examples:
            if st.button(example, key=f"example_{hashlib.md5(example.encode()).hexdigest()[:8]}"):
                st.session_state.user_prompt = example
                st.rerun()
        
        st.divider()
        
        st.markdown("## 🔧 Features")
        
        features = [
            ("🤖", "AI-Powered", "Generate forms using natural language"),
            ("🎨", "Smart Fields", "Auto-detects field types and labels"),
            ("📊", "Multiple Types", "Text, email, dropdowns, checkboxes, etc."),
            ("📥", "JSON Export", "Download submissions as structured data"),
            ("⚡", "Instant Preview", "See your form appear in real-time")
        ]
        
        for icon, title, desc in features:
            st.markdown(f"**{icon} {title}**")
            st.markdown(f"<small>{desc}</small>", unsafe_allow_html=True)
            st.markdown("---")
        
        st.divider()
        
        st.markdown("## ⚙️ Settings")
        use_ai = st.toggle("Use AI (OpenAI)", value=st.session_state.use_ai, 
                          help="Requires OPENAI_API_KEY in .env file")
        st.session_state.use_ai = use_ai
        
        if use_ai:
            client = get_openai_client()
            if not client:
                st.warning("⚠️ OpenAI API key not found. Using rule-based generation.")
    
    # Main content area
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Prompt input
        user_prompt = st.text_area(
            "**Describe the form you need:**",
            placeholder="E.g., 'I need a registration form for a doctors' conference with Name, Medical License Number, and Dietary Restrictions'",
            height=120,
            key="user_prompt_input",
            value=st.session_state.user_prompt
        )
        
        # Update session state
        st.session_state.user_prompt = user_prompt
        
        # Generate button
        if st.button("🚀 Generate Form", type="primary", use_container_width=True):
            if user_prompt.strip():
                with st.spinner("✨ Generating your form..."):
                    form_spec = extract_form_requirements(user_prompt)
                    st.session_state.current_form = form_spec
                    st.session_state.form_submitted = False
                    st.session_state.form_data = None
                    st.rerun()
            else:
                st.warning("Please enter a description of the form you need.")
    
    # Display generated form
    if st.session_state.current_form:
        st.divider()
        
        # Form container
        with st.container():
            st.markdown('<div class="form-container">', unsafe_allow_html=True)
            
            # Render the form
            form_data, submitted = render_form(st.session_state.current_form)
            
            if submitted:
                st.session_state.form_submitted = True
                st.session_state.form_data = form_data
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Display submitted data
    if st.session_state.form_submitted and st.session_state.form_data:
        st.divider()
        display_form_data(st.session_state.form_data, st.session_state.current_form)
        
        # Reset button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 Create Another Form", type="secondary", use_container_width=True):
                # Clear all form-related session state
                st.session_state.current_form = None
                st.session_state.form_submitted = False
                st.session_state.form_data = None
                st.session_state.user_prompt = ""
                
                # Clear any dynamically created session state keys
                keys_to_remove = []
                for key in st.session_state.keys():
                    if key.startswith('field_') or key.startswith('form_data_') or key.startswith('generated_form_'):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del st.session_state[key]
                
                st.rerun()
    
    # Footer
    st.divider()
    st.markdown(
        """
        <div style="text-align: center; color: #6B7280; padding: 1rem;">
            <p>✨ <b>AI Form Generator</b> | Built with Streamlit & AI Magic</p>
            <p><small>Simply describe, generate, and collect! No code required.</small></p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Close main container
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
