CREATE TABLE raw_data (
    Request_ID VARCHAR(10) PRIMARY KEY,
    date VARCHAR(20),
    name VARCHAR(200),
    street VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(10),
    zip VARCHAR(20),
    thematic_area VARCHAR(100),
    financial_year VARCHAR(10),
    feasibility NUMERIC,
    capital_costs NUMERIC,
    operational_costs NUMERIC,
    mobilization NUMERIC,
    project_management NUMERIC,
    grand_total NUMERIC
);
