import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
import json
from PIL import Image
import io
import os
import glob

def process_insurance_form(folder_path: str):
    image_parts = []
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp')

    if not os.path.isdir(folder_path):
        print(f"Error: Folder not found at {folder_path}")
        return {}

    for file_path in glob.glob(os.path.join(folder_path, '*')):
        if file_path.lower().endswith(valid_extensions):
            try:
                with Image.open(file_path) as pil_image:
                    img_byte_arr = io.BytesIO()
                    pil_image.save(img_byte_arr, format=pil_image.format)
                    img_byte_arr = img_byte_arr.getvalue()
                    image_parts.append(Part.from_data(data=img_byte_arr, mime_type=f"image/{pil_image.format.lower()}"))
            except Exception as e:
                print(f"Warning: Could not process image {file_path}: {e}")

    if not image_parts:
        print(f"Error: No valid images found in {folder_path}")
        return {}

    # TODO(user): Configure Vertex AI project and location.
    # Replace 'your-project-id' and 'your-location' with your actual GCP project ID and region.
    # Ensure you have authenticated to GCP (e.g., `gcloud auth application-default login`)
    vertexai.init(project='titanium-vigil-470905-d2', location='asia-southeast1')

    system_instruction_content = """
You are an AI assistant specialized in extracting information from insurance forms and NID cards.
Review all provided images (forms and IDs). Extract the Name, Age, NID, Medical History, Permanent Address (from NID), and Product Information.

**Extraction Rules:**
- **Name:** Extract in both English and Bengali.
- **Age:** Extract as an integer.
- **National ID (NID):** Extract the NID number.
- **Medical History:** Extract in both English and Bengali, summarize if lengthy.
- **Permanent_Address:** Extract ONLY from the NID card, in a structured Bangladesh format. Include sub-fields for:
    - Village_House_Road_English: (String)
    - Village_House_Road_Bengali: (String)
    - Post_Office: (String)
    - Post_Code: (String)
    - Upazila_PS: (String, Police Station)
    - District: (String)
    - Full_Address_English: (String, Aggregated full address)
    - Full_Address_Bengali: (String, Aggregated full address)
- **Product_Information:** Extract from the policy tables. Include:
    - Plan_Name_English: (String, e.g., 'Sanchay' or 'Endowment')
    - Plan_Name_Bengali: (String)
    - Policy_Term_Years: (Integer)
    - Sum_Assured_Amount: (String with currency, e.g., '5,00,000 BDT')
    - Premium_Mode: (String, e.g., 'Monthly/মাসিক', 'Quarterly', 'Yearly')

**Cross-Verification & Aggregation:**
- Cross-verify the NID card data against the form data. If there is a mismatch in NID, flag it.
- If the Plan details are split across multiple pages (images), aggregate them into a single coherent object.

Respond strictly in the following JSON format. If a field or sub-field is not found, use an empty string for string values, 0 for integer values, and false for boolean flags.

{
  "Name_English": "Value",
  "Name_Bengali": "Value",
  "Age": 0,
  "NID": "Value",
  "NID_Mismatch_Flag": false, // true if NID on form and ID card do not match
  "NID_Mismatch_Details": "", // Provide details if a mismatch is found
  "Permanent_Address": {
    "Village_House_Road_English": "",
    "Village_House_Road_Bengali": "",
    "Post_Office": "",
    "Post_Code": "",
    "Upazila_PS": "",
    "District": "",
    "Full_Address_English": "",
    "Full_Address_Bengali": ""
  },
  "Product_Information": {
    "Plan_Name_English": "",
    "Plan_Name_Bengali": "",
    "Policy_Term_Years": 0,
    "Sum_Assured_Amount": "",
    "Premium_Mode": ""
  },
  "Medical_History_English": "Value",
  "Medical_History_Bengali": "Value"
}
"""
    model = GenerativeModel("gemini-2.5-flash", system_instruction=[system_instruction_content])

    try:
        user_prompt = "Review the provided insurance forms and ID cards. Extract the requested information and perform NID cross-verification."

        generation_config = {
            "response_mime_type": "application/json",
        }

        contents = image_parts + [user_prompt]
        response = model.generate_content(contents, generation_config=generation_config)

        # Assuming the model's response is directly a JSON string
        extracted_data = json.loads(response.text)
        return extracted_data

    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

if __name__ == "__main__":
    # TODO(user): Replace with the actual path to your folder containing insurance forms and ID images.
    # Example: image_folder_path = "D:\\VertexAIExp\\Applicant1"
    image_folder_path = "D:\\VertexAIExp\\UW\\Applicant1"

    print(f"Processing images in folder: {image_folder_path}")
    extracted_info = process_insurance_form(image_folder_path)

    output_filename = "extracted_data.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(extracted_info, f, ensure_ascii=False, indent=4)

    print(f"Extracted data saved to {output_filename}")
    print(json.dumps(extracted_info, indent=4, ensure_ascii=False))
