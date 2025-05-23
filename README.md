# Data Mesh Hackathon Workshop

Welcome to the **Data Mesh Hackathon**! This workshop demonstrates how to build a modular, scalable, and collaborative data platform using modern open-source components.

## Tech Stack

This project uses the following tools, all running via **Docker Compose**:

| Component            | Purpose                                         |
|----------------------|-------------------------------------------------|
| **Apache Airflow**   | Data pipeline orchestration (ETL)               |
| **Trino**            | SQL query engine across MinIO/Iceberg           |
| **MinIO**            | S3-compatible object storage                    |
| **Apache Iceberg**   | Table format for big data analytics (via Hive)  |
| **Hive Metastore**   | Catalog for Iceberg tables                      |
| **Jupyter Notebook** | Interactive analysis for data scientists        |
| **Apache Superset**  | Dashboards and visualizations for analysts      |

---

# Prerequisites
Before running this project, make sure you have the following installed and configured on your machine:

## System Requirements

Operating System: macOS, Linux, or Windows

Memory: minimum 8 GB RAM allocated to Docker

## Tools
Tool	    Version (Recommended)
Docker	    20.10+	Container runtime
Docker      Compose	v2.0+	Multi-container orchestration
Git	        stable version	Clone and manage the repository
Python (Optional)	3.9+	Run local scripts/debug steps



## Architecture Overview
```
[ Airflow ] --> [ XLS Processing + Transform ]
↓
[ Trino ]   → [ Write to Iceberg / MinIO ]
↓
[ Jupyter Notebook ] ← View & Analyze
↓
[ Superset ] ← Build Dashboards
```
## Project Structure
```
finos-hackathon/
├── airflow/ # Airflow DAGs and config
├── notebooks/ # Jupyter notebooks
├── dashboards/ # Superset dashboards (optional exports)
├── docker-compose.yml # Compose for all services
├── dags/
│ └── xls_etl_pipeline.py # Airflow DAG to process XLS files
├── scripts/
│ └── transform.py # Business logic for transformation
├── README.md # This file
```
## Pipeline Flow
1. **Airflow DAG** triggers on new XLS files.
2. Applies **data transformation and business rules** (via Python script).
3. Extracts **key fields** and outputs a clean dataset.
4. Writes processed data to **Iceberg table on MinIO** using **Trino**.
5. **Jupyter Notebook** lets data scientists explore the processed data.
6. **Superset** builds dashboards for analysts using the same Trino connection.

## Transformation Logic

As part of the ETL pipeline, we standardize and clean incoming data using the following rules:

### Field Mappings
```
| Field                       | Raw Value | Transformed Value             |
|-----------------------------|-----------|-------------------------------|
| **Channel**                 | R         | Retail                        |
|                             | B         | Broker                        |
|                             | C         | Correspondent                 |
|                             | T         | TPO Not Specified             |
|                             | 9         | Not Available                 |
--------------------------------------------------------------------------
| **First Time Home Buyer**   | Y         | Yes                           |
|                             | N         | No                            |
---------------------------------------------------------------------------
| **Loan Purpose**            | P         | Purchase                      |
|                             | C         | Refinance - Cash Out          |
|                             | N         | Refinance - No Cash Out       |
|                             | R         | Refinance - Not Specified     |
|                             | 9         | Not Available                 |
```
### Extracted Fields
```
The following **key fields** are cleansed and  extracted from the from source and persisted in S3 bucket:

```python
REQUIRED_COLUMNS = [
    "Reference Pool ID", "Loan Identifier", "Monthly Reporting Period", "Channel",
    "Seller Name", "Servicer Name", "Master Servicer", "Original Interest Rate",
    "Current Interest Rate", "Original UPB", "UPB at Issuance", "Current Actual UPB",
    "Original Loan Term", "Origination Date", "First Payment Date", "Loan Age",
    "Remaining Months to Legal Maturity", "Remaining Months To Maturity", "Maturity Date",
    "Original Loan to Value Ratio (LTV)", "Original Combined Loan to Value Ratio (CLTV)",
    "Number of Borrowers", "Debt-To-Income (DTI)", "Borrower Credit Score at Origination",
    "Co-Borrower Credit Score at Origination", "First Time Home Buyer Indicator",
    "Loan Purpose", "Property Type", "Number of Units", "Occupancy Status",
    "Property State", "Metropolitan Statistical Area (MSA)", "Zip Code Short",
    "Mortgage Insurance Percentage", "Amortization Type", "Prepayment Penalty Indicator",
    "Interest Only Loan Indicator", "Interest Only First Principal And Interest Payment Date",
    "Months to Amortization", "Current Loan Delinquency Status", "Loan Payment History",
    "Modification Flag"
]
```
## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-org/finos-hackathon.git
cd finos-hackathon

docker-compose up -d
```

# Url enf point for all the components

```
| Service          | URL                                            |credentials)
|                                                                   | userid-passowrd   
| ---------------- | ---------------------------------------------- |-----------------
| Airflow          | [http://localhost:8080](http://localhost:8080) | airflow - airflow
| Jupyter Notebook | [http://localhost:8888](http://localhost:8888) | NA
| Superset         | [http://localhost:8088](http://localhost:8088) | admin/admin
| MinIO Console    | [http://localhost:9001](http://localhost:9001) | minioAdmin/minio1234
| Trino UI         | [http://localhost:8081](http://localhost:8081) | Admin / NA

```
