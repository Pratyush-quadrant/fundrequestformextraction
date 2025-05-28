import os
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta
from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions
)
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential


from db_upload import insert_to_postgres

load_dotenv()

BLOB_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER")
DOC_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
DOC_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

def upload_and_process_file(file_path):
    filename = os.path.basename(file_path)

    # Upload PDF to Azure Blob Storage
    blob_service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
    blob_client = blob_service.get_blob_client(container=CONTAINER_NAME, blob=filename)
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    # Generate secure SAS URL for Document Intelligence access
    blob_url = generate_sas_url(filename)

    # Analyze PDF using Azure Document Intelligence prebuilt-document model
    doc_client = DocumentAnalysisClient(
        endpoint=DOC_ENDPOINT,
        credential=AzureKeyCredential(DOC_KEY)
    )
    poller = doc_client.begin_analyze_document_from_url("prebuilt-document", blob_url)
    result = poller.result()

    # Extract all lines from all pages
    lines = []
    for page in result.pages:
        for line in page.lines:
            lines.append(line.content.strip())

    # DEBUG: Print all extracted lines from PDF
    print("DEBUG: Extracted lines from PDF:")
    for line in lines:
        print(repr(line))

    # Define the field order for vertical fields (based on layout)
    vertical_fields = [
        "name",
        "street",
        "city",
        "state",
        "zip",
        "thematic area",
        "financial year"
    ]

    # Prepare a mapping for extracted data
    data = {
        "date": None,
        "name": None,
        "street": None,
        "city": None,
        "state": None,
        "zip": None,
        "thematic_area": None,
        "financial_year": None,
        "feasibility": None,
        "capital_costs": None,
        "operational_costs": None,
        "mobilization": None,
        "project_management": None,
        "grand_total": None
    }

    # 1. Extract date (first line matching date pattern)
    for line in lines:
        if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", line):
            data["date"] = line
            break

    # 2. Extract vertical fields by scanning for the field, then taking the next non-empty line
    def extract_vertical_field(field_label):
        for i, line in enumerate(lines):
            if line.lower() == field_label:
                # Look for the next non-empty line
                for j in range(i+1, len(lines)):
                    next_line = lines[j].strip()
                    # Don't allow the next line to be another field label
                    if next_line and next_line.lower() not in vertical_fields:
                        return next_line
        return None

    # Extract all vertical fields
    for field in vertical_fields:
        val = extract_vertical_field(field)
        key = field.replace(" ", "_")
        data[key] = val

    # 3. Extract cost details from tables
    for table in result.tables:
        # Build rows as lists of cell contents
        table_rows = {}
        for cell in table.cells:
            if cell.row_index not in table_rows:
                table_rows[cell.row_index] = []
            table_rows[cell.row_index].append(cell.content.strip())
        # Now, for each row, look for cost categories
        for row in table_rows.values():
            row_lc = [r.lower() for r in row]
            if any("feasibility" in r for r in row_lc):
                data["feasibility"] = parse_amount(row)
            elif any("capital" in r for r in row_lc):
                data["capital_costs"] = parse_amount(row)
            elif any("operational" in r for r in row_lc):
                data["operational_costs"] = parse_amount(row)
            elif any("mobilization" in r for r in row_lc):
                data["mobilization"] = parse_amount(row)
            elif any("project mgmnt" in r or "project management" in r or "project_mgmnt" in r for r in row_lc):
                data["project_management"] = parse_amount(row)
            elif any("grand total" in r or "grant total" in r for r in row_lc):
                data["grand_total"] = parse_amount(row, allow_dollar_last=True)

    # INSERT INTO POSTGRESQL DATABASE
    insert_to_postgres(data, filename)

    return data

def parse_amount(row, allow_dollar_last=False):
    # Find the last numeric value in the row (ignore $ sign if it's a separate cell)
    for cell in reversed(row):
        
        if allow_dollar_last and cell.strip() == "$":
            continue
        # Remove $ and commas and parse
        val = cell.replace("$", "").replace(",", "").replace(" ", "")
        try:
            return float(val)
        except Exception:
            continue
    return None

def generate_sas_url(blob_name):
    parts = dict(part.split("=", 1) for part in BLOB_CONNECTION_STRING.split(";") if "=" in part)
    account_name = parts.get("AccountName")
    account_key = parts.get("AccountKey")
    if not account_name or not account_key:
        raise ValueError("Could not parse AccountName or AccountKey from connection string.")
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=CONTAINER_NAME,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )
    return f"https://{account_name}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}?{sas_token}"
