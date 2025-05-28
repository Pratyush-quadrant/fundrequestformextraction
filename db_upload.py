import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# Read connection info from your .env file
PG_HOST = os.getenv("PG_HOST")  
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER")  
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE", "goodwill_foundation_db")

def insert_to_postgres(data, pdf_filename):
    # Extract Request_ID from filename (e.g., FR01.pdf -> FR01)
    request_id = os.path.splitext(pdf_filename)[0]

    # Prepare the row
    row = (
        request_id,
        data.get("date"),
        data.get("name"),
        data.get("street"),
        data.get("city"),
        data.get("state"),
        data.get("zip"),
        data.get("thematic_area"),
        data.get("financial_year"),
        data.get("feasibility"),
        data.get("capital_costs"),
        data.get("operational_costs"),
        data.get("mobilization"),
        data.get("project_management"),
        data.get("grand_total")
    )

    insert_sql = """
    INSERT INTO raw_data (
        Request_ID, date, name, street, city, state, zip, thematic_area, financial_year,
        feasibility, capital_costs, operational_costs, mobilization, project_management, grand_total
    ) VALUES %s
    ON CONFLICT (Request_ID) DO UPDATE SET
        date = EXCLUDED.date,
        name = EXCLUDED.name,
        street = EXCLUDED.street,
        city = EXCLUDED.city,
        state = EXCLUDED.state,
        zip = EXCLUDED.zip,
        thematic_area = EXCLUDED.thematic_area,
        financial_year = EXCLUDED.financial_year,
        feasibility = EXCLUDED.feasibility,
        capital_costs = EXCLUDED.capital_costs,
        operational_costs = EXCLUDED.operational_costs,
        mobilization = EXCLUDED.mobilization,
        project_management = EXCLUDED.project_management,
        grand_total = EXCLUDED.grand_total;
    """

    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DATABASE,
        sslmode='require'
    )
    try:
        with conn:
            with conn.cursor() as cur:
                execute_values(cur, insert_sql, [row])
        print(f"Inserted/updated data for {request_id}")
    finally:
        conn.close()
