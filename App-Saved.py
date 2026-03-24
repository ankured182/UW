import os
import streamlit as st
import PIL.Image
import json
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError

# 1. UI CONFIGURATION
st.set_page_config(page_title="Sonali Life AI Underwriter", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #0056b3; color: white; border-radius: 8px; width: 100%; }
    .status-pass { color: #28a745; font-weight: bold; }
    .status-flag { color: #dc3545; font-weight: bold; }
    .stImage { border-radius: 5px; border: 1px solid #ddd; background: white; padding: 2px; }
    .address-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
    .address-table td { border: 1px solid #dee2e6; padding: 8px; }
    .address-header { background-color: #f8f9fa; font-weight: bold; width: 40%; }
    </style>
    """, unsafe_allow_html=True)

st.title("Sonali Life: AI Underwriter")
st.subheader("Single Applicant Processing (Gemini 3.1 Pro Preview)")

# --- INITIALIZE SESSION STATE ---
if "applicant_data" not in st.session_state:
    st.session_state.applicant_data = None
    st.session_state.images = None
    st.session_state.processing_time = None

# 2. SIDEBAR
with st.sidebar:
    st.header("System Status")
    project_id = os.getenv("GCP_PROJECT_ID", "titanium-vigil-470905-d2")
    location = os.getenv("GCP_LOCATION", "global") 
    st.info(f"Connected to Vertex AI\nProject: {project_id}\nLocation: {location}\nModel: Gemini 3.1 Pro Preview\nResolution: Raw/Uncompressed")

# 3. UPLOAD ZONE
uploaded_files = st.file_uploader("Upload ALL Documents for ONE Applicant", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])

if st.button("Process Applicant"):
    if uploaded_files:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Preparing raw images for high-fidelity upload...")
        images = []
        for f in uploaded_files:
            img = PIL.Image.open(f)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            images.append(img)
            
        st.session_state.images = images

        success = False
        retries = 3
        
        while not success and retries > 0:
            try:
                status_text.text(f"Uploading {len(images)} raw documents to Gemini 3.1 Pro (Global)... Please wait.")
                
                client = genai.Client(vertexai=True, project=project_id, location=location)
                
                prompt = """
                You are an expert in Bengali and English Document OCR. Read the handwritten and printed Bengali text exactly as it appears, stroke-for-stroke. DO NOT auto-correct or guess spellings.

                Analyze ALL the provided images. They contain Life Insurance application pages and ID documents (NID/Passport/Birth Certificate) for exactly ONE single applicant and their nominee.
                
                Extract the following and return a SINGLE JSON OBJECT.
                
                1. doc_mapping: Set "page_1_index" to the exact integer index (0-based) of the image in the provided list that represents Page 1 for this specific applicant.
                2. Extract Names (EN/BN): Applicant, Father, Mother, and Spouse. Translate if missing.
                2a. Extract Applicant's Date of Birth: Look specifically at the National ID card or Photo ID and extract the "Date of Birth".
                3. Extract Contact: Mobile Number (Remove Hyphen/Country Code) and NID Number from Page 1.
                4. Extract Address: Parse the ID Document of the Applicant Permanent Address into Village/Street, Post Office, Upazila, and District in Bengali. Provide English Translation.
                5. Extract Nominee: Name (EN/BN), Relation (EN/BN), Date of Birth if available, ID document number if available, and Allocation % if mentioned (if 1 applicant then 100% allocation).
                6. Underwriting (Medical): Analyze the medical questionnaire page. An 'AUTO-PASS' requires that the applicant is currently healthy ('Yes' to being healthy) AND has answered 'No' to ALL adverse health questions (e.g., diseases, surgeries, unexpected weight changes, hospitalizations, or disabilities). If the applicant declares ANY medical issues, diseases, or red flags, set status to 'REQUIRES-REVIEW'. 
                6a. Extract Opted Policy/Plan Details: Locate the "Product Information" (পরিকল্প সংক্রান্ত তথ্য) section on Page 2. You must apply STRICT VISUAL GROUNDING. Extract exactly what is written in the boxes. DO NOT guess, calculate, or assume values. If a box is physically empty, you MUST return "Blank".
                - "Premium Amount": Read the handwritten Bengali numerals carefully (e.g., ২,০০০/-). Do not add zeroes.
                - "Sum Assured" (বীমা অংক): If the box is empty, return "Blank". Do not invent a standard policy amount.
                - "Installment Type / Mode of Payment" (প্রিমিয়াম জমা পদ্ধতি): Look very closely for a handwritten pen stroke or tick mark (✓) over the printed checkboxes (Yearly, Half Yearly, Quarterly, Monthly, Single). Return ONLY the option that contains the handwritten tick mark.
                - "Name of Plan" (পরিকল্পের নাম): Extract the exact handwritten text (e.g., ৫ কিস্তি).
                - "Product No" and "Term": Extract exactly what is handwritten.
                7. Verification (Identity): Compare handwriting on Page 1 with the NID card. Return confidence_score as an INTEGER (0-100).
                8. Photo Detection: Detect [ymin, xmin, ymax, xmax] bounding boxes for the Applicant and Nominee photos on their respective Page 1.

                Return strictly valid JSON in this exact schema:
                {
                  "doc_mapping": {"page_1_index": 0},
                  "applicant_details": {
                      "name_english": "", "name_bengali": "", "mobile": "", "doc_nid": "",
                      "father_name_english": "", "father_name_bengali": "",
                      "mother_name_english": "", "mother_name_bengali": "",
                      "spouse_name_english": "", "spouse_name_bengali": "",
                      "date_of_birth_nid": ""
                  },
                  "verification": {"identity_verified": false, "confidence_score": 0, "reasoning": ""},
                  "nominee_details": {"name_english": "", "name_bengali": "", "relation_english": "", "relation_bengali": "", "dob": "", "id_number": "", "allocation_percentage": ""},
                  "medical_underwriting": {"status": "", "summary": ""},
                  "address_breakdown": {
                      "village_bn": "", "post_office_bn": "", "upazila_bn": "", "district_bn": "",
                       "village_en": "", "post_office_en": "", "upazila_en": "", "district_en": "",  
                       "full_bengali": "", "full_english": ""
                  },
                  "passport_photo_boxes": {"page_1_applicant": [0,0,0,0], "page_1_nominee": [0,0,0,0]},
                  "product_details": {
                      "plan_name_english": "", "plan_name_bengali": "",
                      "product_no": "",
                      "term_english": "", "term_bengali": "",
                      "sum_assured": "",
                      "premium_amount": "",
                      "installment_type_english": "", "installment_type_bengali": ""
                  }
                }
                """
                
                start_time = time.time()
                
                response = client.models.generate_content(
                    model='gemini-3.1-pro-preview',
                    contents=[*images, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.0
                    )
                )

                end_time = time.time()
                st.session_state.processing_time = end_time - start_time

                item = json.loads(response.text)
                
                st.session_state.applicant_data = item
                
                success = True
                status_text.success(f"Processing complete! API Time taken: {st.session_state.processing_time:.2f} seconds")
                progress_bar.progress(1.0)
                
            except ServerError:
                retries -= 1
                status_text.warning("Server busy. Retrying after sleep...")
                time.sleep(5)
            except Exception as e:
                st.error(f"Error processing document: {e}")
                break

# --- RENDER UI FROM SESSION STATE ---
if st.session_state.applicant_data:
    item = st.session_state.applicant_data
    images = st.session_state.images

    st.markdown("---")
    
    if st.session_state.processing_time:
        st.info(f"⚡ Extraction Speed: {st.session_state.processing_time:.2f} seconds via Global (Gemini 3.1 Pro)")

    col_photos, col_details = st.columns([1, 2])
    
    p1_idx = item.get('doc_mapping', {}).get('page_1_index', 0)
    
    if p1_idx < len(images):
        form_p1 = images[p1_idx]
        W, H = form_p1.size

        with col_photos:
            try:
                ab = item.get('passport_photo_boxes', {}).get('page_1_applicant', [0,0,0,0])
                if sum(ab) > 0:
                    st.image(form_p1.crop((ab[1]*W/1000, ab[0]*H/1000, ab[3]*W/1000, ab[2]*H/1000)), caption="Applicant", width=150)
                
                nb = item.get('passport_photo_boxes', {}).get('page_1_nominee', [0,0,0,0])
                if sum(nb) > 0:
                    st.image(form_p1.crop((nb[1]*W/1000, nb[0]*H/1000, nb[3]*W/1000, nb[2]*H/1000)), caption="Nominee", width=150)
            except Exception as e:
                st.warning(f"Could not crop photos: {e}")

    with col_details:
        score = item.get('verification', {}).get('confidence_score', 0)
        p_score = score if score > 1 else score * 100
        v_color = "status-pass" if p_score > 90 else "status-flag"
        st.markdown(f"**ID Match Score:** <span class='{v_color}'>{int(p_score)}%</span>", unsafe_allow_html=True)                                                
        
        app_details = item.get('applicant_details', {})
        st.write(f"**Applicant Name:** {app_details.get('name_english')} | {app_details.get('name_bengali')}")
        st.write(f"**Applicant DoB (from ID):** {app_details.get('date_of_birth_nid', 'N/A')}")
        st.write(f"**Mobile:** {app_details.get('mobile')} | **ID Number:** {app_details.get('doc_nid')}")
        
        st.markdown("### Family and Nominee Details")
        st.write(f"**Mother:** {app_details.get('mother_name_english')} | {app_details.get('mother_name_bengali')}")
        st.write(f"**Father:** {app_details.get('father_name_english')} | {app_details.get('father_name_bengali')}")
        st.write(f"**Spouse:** {app_details.get('spouse_name_english')} | {app_details.get('spouse_name_bengali')}")
        
        nom_details = item.get('nominee_details', {})
        st.write(f"**Nominee:** {nom_details.get('name_english')} ({nom_details.get('relation_english')})")
        if nom_details.get('dob'):
            st.write(f"**Nominee DOB:** {nom_details.get('dob')}")
        if nom_details.get('id_number'):
            st.write(f"**Nominee ID:** {nom_details.get('id_number')}")
        if nom_details.get('allocation_percentage'):
            st.write(f"**Allocation:** {nom_details.get('allocation_percentage')}")
        
        st.markdown("### Opted Policy / Plan Details")
        prod_details = item.get('product_details', {})
        if prod_details:
            st.write(f"**Plan:** {prod_details.get('plan_name_english', 'N/A')} | {prod_details.get('plan_name_bengali', 'N/A')}")
            st.write(f"**Product No:** {prod_details.get('product_no', 'N/A')} | **Term:** {prod_details.get('term_english', 'N/A')} | {prod_details.get('term_bengali', 'N/A')}")
            st.write(f"**Sum Assured:** {prod_details.get('sum_assured', 'N/A')}")
            st.write(f"**Premium Amount:** {prod_details.get('premium_amount', 'N/A')}")
            st.write(f"**Installment Type:** {prod_details.get('installment_type_english', 'N/A')} | {prod_details.get('installment_type_bengali', 'N/A')}")
            
        st.markdown("#### Medical")
        med_details = item.get('medical_underwriting', {})
        st.write(f"**Medical Status:** {med_details.get('status')}")
        st.write(f"**AI Medical Summary:** {med_details.get('summary')}")

        st.markdown("#### Address")
        addr = item.get('address_breakdown', {})
        st.markdown(f"""
        <table class="address-table">
            <tr><td class="address-header">Village/Street</td><td>{addr.get('village_bn', 'N/A')}</td><td>{addr.get('village_en', 'N/A')}</td></tr>
            <tr><td class="address-header">Post Office</td><td>{addr.get('post_office_bn', 'N/A')}</td><td>{addr.get('post_office_en', 'N/A')}</td></tr>
            <tr><td class="address-header">Upazila</td><td>{addr.get('upazila_bn', 'N/A')}</td><td>{addr.get('upazila_en', 'N/A')}</td></tr>
            <tr><td class="address-header">District</td><td>{addr.get('district_bn', 'N/A')}</td><td>{addr.get('district_en', 'N/A')}</td></tr>
        </table>
        """, unsafe_allow_html=True)