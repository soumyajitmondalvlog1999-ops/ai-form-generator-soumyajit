import streamlit as st
import json
import re
from typing import Dict, List, Optional, Any
import os
from openai import OpenAI
from dotenv import load_dotenv
import jsonschema
from jsonschema import validate

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
        st.error("Please set your OPENAI_API_KEY in a .env file or environment variables")
        st.info("Create a `.env` file with: OPENAI_API_KEY=your_key_here")
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
    if client:
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
            st.warning(f"AI parsing failed: {e}. Using fallback generator.")
    
    # Fallback: Generate simple form based on keywords
    return generate_simple_form(prompt)

def generate_simple_form(prompt: str) -> Dict:
    """Generate a simple form based on keywords in the prompt"""
    # Extract field names from prompt
    field_keywords = {
        "name": ["name", "full name", "first name", "last name"],
        "email": ["email", "e-mail"],
        "phone": ["phone", "mobile", "telephone", "contact number"],
        "date": ["date", "dob", "birth", "appointment"],
        "number": ["number", "id", "license", "registration"],
        "textarea": ["description", "comments", "feedback", "pain points", "details"],
        "select": ["category", "type", "gender", "country", "state"],
        "checkbox": ["agree", "terms", "accept", "subscribe"]
    }
    
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
    
    # Generate title from prompt
    words = prompt.split()[:5]
    title = " ".join(words) + " Registration Form"
    
    return {
        "title": title,
        "description": f"Form generated from: '{prompt}'",
        "fields": fields
    }

def render_form(form_spec: Dict) -> Dict:
    """
    Render the form using Streamlit components
    Returns dictionary of form values
    """
    st.markdown(f"## {form_spec['title']}")
    if 'description' in form_spec:
        st.markdown(form_spec['description'])
    
    st.divider()
    
    form_data = {}
    
    with st.form(key="generated_form"):
        for field in form_spec['fields']:
            field_name = field['name']
            field_label = field['label']
            field_type = field['field_type']
            required = field.get('required', False)
            placeholder = field.get('placeholder', '')
            options = field.get('options', [])
            
            # Add required indicator to label
            display_label = f"{field_label} {'*' if required else ''}"
            
            # Render different field types
            if field_type == "text":
                form_data[field_name] = st.text_input(
                    display_label,
                    placeholder=placeholder,
                    value=st.session_state.get(field_name, "")
                )
            elif field_type == "email":
                form_data[field_name] = st.text_input(
                    display_label,
                    placeholder=placeholder,
                    value=st.session_state.get(field_name, "")
                )
            elif field_type == "number":
                form_data[field_name] = st.number_input(
                    display_label,
                    value=st.session_state.get(field_name, 0),
                    step=1
                )
            elif field_type == "tel":
                form_data[field_name] = st.text_input(
                    display_label,
                    placeholder=placeholder,
                    value=st.session_state.get(field_name, "")
                )
            elif field_type == "textarea":
                form_data[field_name] = st.text_area(
                    display_label,
                    placeholder=placeholder,
                    value=st.session_state.get(field_name, ""),
                    height=100
                )
            elif field_type == "select":
                form_data[field_name] = st.selectbox(
                    display_label,
                    options=options,
                    index=0
                )
            elif field_type == "multiselect":
                form_data[field_name] = st.multiselect(
                    display_label,
                    options=options,
                    default=st.session_state.get(field_name, [])
                )
            elif field_type == "date":
                form_data[field_name] = st.date_input(display_label)
            elif field_type == "checkbox":
                form_data[field_name] = st.checkbox(display_label)
            
            # Store in session state for persistence
            st.session_state[field_name] = form_data[field_name]
        
        # Submit button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("Submit Form", type="primary", use_container_width=True)
    
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
            st.write(f"**{field_label}:** {value if value not in [None, ''] else 'Not provided'}")
    
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
        mime="application/json"
    )

def main():
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1E3A8A;
            text-align: center;
            margin-bottom: 1rem;
        }
        .sub-header {
            font-size: 1.2rem;
            color: #4B5563;
            text-align: center;
            margin-bottom: 2rem;
        }
        .stButton button {
            width: 100%;
            background-color: #3B82F6;
            color: white;
            font-weight: bold;
        }
        .stTextInput input {
            border-radius: 8px;
        }
        .form-container {
            background-color: #F9FAFB;
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid #E5E7EB;
        }
        </style>
    """, unsafe_allow_html=True)
    
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
        
        for example in examples:
            if st.button(example, key=f"ex_{example[:10]}"):
                st.session_state.user_prompt = example
                st.rerun()
        
        st.divider()
        
        st.markdown("## 🔧 Features")
        st.markdown("""
        - **Natural Language Processing**: Describe forms in plain English
        - **Multiple Field Types**: Text, email, dropdowns, checkboxes, etc.
        - **Smart Mapping**: Auto-generates labels and placeholders
        - **JSON Export**: Download submissions as structured data
        """)
        
        st.divider()
        
        st.markdown("## ⚙️ Settings")
        use_ai = st.toggle("Use AI (OpenAI)", value=True, help="Requires OPENAI_API_KEY in .env file")
        st.session_state.use_ai = use_ai
    
    # Main content area
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Prompt input
        user_prompt = st.text_area(
            "Describe the form you need:",
            placeholder="E.g., 'I need a registration form for a doctors' conference with Name, Medical License Number, and Dietary Restrictions'",
            height=100,
            key="user_prompt"
        )
        
        # Generate button
        if st.button("Generate Form", type="primary", use_container_width=True):
            if user_prompt.strip():
                with st.spinner("Generating your form..."):
                    form_spec = extract_form_requirements(user_prompt)
                    st.session_state.current_form = form_spec
                    st.session_state.form_submitted = False
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
        if st.button("Create Another Form", type="secondary"):
            st.session_state.current_form = None
            st.session_state.form_submitted = False
            st.session_state.form_data = None
            for key in list(st.session_state.keys()):
                if key not in ['current_form', 'form_submitted', 'form_data', 'use_ai']:
                    del st.session_state[key]
            st.rerun()
    
    # Footer
    st.divider()
    st.markdown(
        """
        <div style="text-align: center; color: #6B7280; padding: 1rem;">
            <p>AI Form Generator | Built with Streamlit</p>
            <p>Simply describe, generate, and collect!</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()