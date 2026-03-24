import streamlit as st
import json
import os
from PIL import Image
import glob

# --- Configuration --- #
DATA_FILE = r"extracted_data.json"
IMAGE_FOLDER = r"D:\VertexAIExp\Applicant1"

# --- Helper Functions ---
def load_extracted_data(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# --- Streamlit UI --- #
st.set_page_config(layout="wide", page_title="Underwriting Dashboard")
st.title("Insurance Underwriting Dashboard")

data = load_extracted_data(DATA_FILE)

if data:
    st.header(f"Applicant: {data.get('Name_English', 'N/A')} (Age: {data.get('Age', 'N/A')})")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Applicant Documents")
        image_paths = []
        valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        if os.path.isdir(IMAGE_FOLDER):
            for file_path in glob.glob(os.path.join(IMAGE_FOLDER, '*')):
                if file_path.lower().endswith(valid_extensions):
                    image_paths.append(file_path)
            
            if image_paths:
                for img_path in sorted(image_paths):
                    try:
                        st.image(img_path, caption=os.path.basename(img_path), use_column_width=True)
                    except Exception as e:
                        st.warning(f"Could not load image {os.path.basename(img_path)}: {e}")
            else:
                st.info(f"No images found in {IMAGE_FOLDER}")
        else:
            st.error(f"Image folder not found: {IMAGE_FOLDER}")

    with col2:
        st.subheader("Extracted Information")

        # Medical History
        medical_history_en = data.get('Medical_History_English', 'N/A')
        medical_history_bn = data.get('Medical_History_Bengali', 'N/A')
        st.markdown(f"""
        ### Medical History
        **English:** {medical_history_en}

        **Bengali:** {medical_history_bn}
        """)

        # NID Status
        nid = data.get('NID', 'N/A')
        nid_mismatch_flag = data.get('NID_Mismatch_Flag', False)
        nid_mismatch_details = data.get('NID_Mismatch_Details', 'No mismatch detected.')

        st.markdown(f"### NID Status")
        st.markdown(f"**NID:** {nid}")
        if nid_mismatch_flag:
            st.error(f"**NID Mismatch Detected!** Details: {nid_mismatch_details}")
        else:
            st.success("NID Verified (No Mismatch).")

        # Permanent Address
        st.markdown("### Permanent Address")
        permanent_address = data.get('Permanent_Address', {})
        st.markdown(f"**Village/House/Road (EN):** {permanent_address.get('Village_House_Road_English', 'N/A')}")
        st.markdown(f"**Village/House/Road (BN):** {permanent_address.get('Village_House_Road_Bengali', 'N/A')}")
        st.markdown(f"**Post Office:** {permanent_address.get('Post_Office', 'N/A')}")
        st.markdown(f"**Post Code:** {permanent_address.get('Post_Code', 'N/A')}")
        st.markdown(f"**Upazila/PS:** {permanent_address.get('Upazila_PS', 'N/A')}")
        st.markdown(f"**District:** {permanent_address.get('District', 'N/A')}")
        st.markdown(f"**Full Address (EN):** {permanent_address.get('Full_Address_English', 'N/A')}")
        st.markdown(f"**Full Address (BN):** {permanent_address.get('Full_Address_Bengali', 'N/A')}")



        # Product Information
        st.markdown("### Product Information")
        product_info = data.get('Product_Information', {})
        st.markdown(f"**Plan Name (EN):** {product_info.get('Plan_Name_English', 'N/A')}")
        st.markdown(f"**Plan Name (BN):** {product_info.get('Plan_Name_Bengali', 'N/A')}")
        st.markdown(f"**Policy Term (Years):** {product_info.get('Policy_Term_Years', 'N/A')}")
        st.markdown(f"**Sum Assured Amount:** {product_info.get('Sum_Assured_Amount', 'N/A')}")
        st.markdown(f"**Premium Mode:** {product_info.get('Premium_Mode', 'N/A')}")

    st.markdown("--- Jardar") # Separator
    st.subheader("Underwriting Decision")
    decision_options = ['Approve', 'Refer to Doctor', 'Reject']
    user_decision = st.radio("Select a decision:", decision_options, index=0)

    if st.button("Submit Decision"):
        st.success(f"Decision submitted: {user_decision}")
        # In a real application, you would save this decision to a database or file

else:
    st.error(f"Could not load data from {DATA_FILE}. Please ensure process_uw_form.py has been run successfully.")
