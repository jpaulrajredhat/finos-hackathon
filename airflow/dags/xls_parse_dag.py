from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import boto3
import os
import pyarrow as pa
import pyarrow.parquet as pq
from trino.dbapi import connect
import re

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET")
ACCESS_KEY = os.environ.get("ACCESS_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")

RAW_XLS = os.environ.get("RAW_XLS")
PARQUET_FILE = os.environ.get("PARQUET_FILE")
S3_OBJECT = os.environ.get("S3_OBJECT")



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

DATE_COLUMNS_MMYYYY = [
    "Monthly Reporting Period",
    "Origination Date",
    "First Payment Date",
    "Maturity Date",
    "Interest Only First Principal And Interest Payment Date"
]

# Define mappings
channel_map = {
    'R': 'Retail',
    'B': 'Broker',
    'C': 'Correspondent',
    'T': 'TPO Not Specified',
    '9': 'Not Available'
}

first_time_buyer_map = {
    'Y': 'Yes',
    'N': 'No'
}

loan_purpose_map = {
    'P': 'Purchase',
    'C': 'Refinance - Cash Out',
    'N': 'Refinance - No Cash Out',
    'R': 'Refinance - Not Specified',
    '9': 'Not Available'
}

def convert_mm_yyyy_to_date(value):
    if pd.isna(value):
        return None
    try:
        return datetime.strptime(str(int(value)), "%m%Y").date().replace(day=1)
    except Exception:
        return None

def apply_transformations(df: pd.DataFrame) -> pd.DataFrame:
    df = df[REQUIRED_COLUMNS].copy()

    for col in DATE_COLUMNS_MMYYYY:
        df[col] = df[col].apply(convert_mm_yyyy_to_date)
        df[col] = pd.to_datetime(df[col], errors='coerce')

    # Handle problematic numeric fields
    df["Current Loan Delinquency Status"] = pd.to_numeric(
        df["Current Loan Delinquency Status"], errors='coerce'
    )

    return df

def sanitize_column_name(col: str) -> str:
    return re.sub(r'\W+', '_', col).strip('_').lower()

def pandas_schema_to_iceberg_org(df):
    schema_lines = []
    for col, dtype in df.dtypes.items():
        col_sanitized = sanitize_column_name(col)
        if pd.api.types.is_integer_dtype(dtype):
            trino_type = "BIGINT"
        elif pd.api.types.is_float_dtype(dtype):
            trino_type = "DOUBLE"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            trino_type = "TIMESTAMP"
        else:
            trino_type = "VARCHAR"
        schema_lines.append(f"{col_sanitized} {trino_type}")
        
    return ",\n".join(schema_lines)

def pandas_schema_to_iceberg(df):
    schema_lines = []
    sanitized_columns = []
    
    for col, dtype in df.dtypes.items():
        col_sanitized = sanitize_column_name(col)
        sanitized_columns.append(col_sanitized)
        
        if pd.api.types.is_integer_dtype(dtype):
            trino_type = "BIGINT"
        elif pd.api.types.is_float_dtype(dtype):
            trino_type = "DOUBLE"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            trino_type = "TIMESTAMP"
        else:
            trino_type = "VARCHAR"
        
        schema_lines.append(f"{col_sanitized} {trino_type}")

    # Update the DataFrame's column names in-place
    df.columns = sanitized_columns
    
    return ",\n".join(schema_lines)

def apply_transform_rules (df):
    
    # print("Available columns:", df.columns.tolist())
    df.columns = df.columns.str.strip()
    # Apply transformations
    df['Channel'] = df['Channel'].map(channel_map).fillna(df['Channel'])
    df['First Time Home Buyer Indicator'] = df['First Time Home Buyer Indicator'].map(first_time_buyer_map).fillna(df['First Time Home Buyer Indicator'])
    # df['Loan Purpose'] = df['Loan Purpose'].map(loan_purpose_map).fillna(df['Loan Purpose'])
    
    if 'Loan Purpose' in df.columns:
        df['Loan Purpose'] = df['Loan Purpose'].map(loan_purpose_map).fillna(df['Loan Purpose'])
    else:
        print("Column 'Loan Purpose' not found.")
    return df 

def transform_and_upload():
    df = pd.read_excel(RAW_XLS, engine="openpyxl")
    
    df = apply_transform_rules(df)

    
    print("Columns in XLS:", df.columns.tolist())

    print("Applying XLS transformations")

    df = apply_transformations(df)
    
    print("apply  xls transform completed", df)


    table = pa.Table.from_pandas(df)
    pq.write_table(table, PARQUET_FILE)

    s3 = boto3.client("s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )

    # Create bucket if not exists
    buckets = s3.list_buckets()
    if MINIO_BUCKET not in [b["Name"] for b in buckets["Buckets"]]:
        s3.create_bucket(Bucket=MINIO_BUCKET)

    s3.upload_file(PARQUET_FILE, MINIO_BUCKET, S3_OBJECT)

def get_column_names(cursor, query):
    cursor.execute(query)
    return [row[0].lower().strip() for row in cursor.fetchall()]

def escape_value(value):
    if pd.isna(value):
        return "NULL"
    elif isinstance(value, str):
        return f"'{value.replace('\'', '\'\'')}'"  # escape single quotes
    elif isinstance(value, pd.Timestamp):
        return f"TIMESTAMP '{value.strftime('%Y-%m-%d %H:%M:%S')}'"
    else:
        return str(value)


def insert_dataframe(cursor, df, table_name, batch_size=100):
    columns = ', '.join(f'"{col}"' for col in df.columns)
    
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        values_sql = []

        for _, row in batch.iterrows():
            row_values = [escape_value(row[col]) for col in df.columns]
            values_sql.append(f"({', '.join(row_values)})")

        query = f"""
        INSERT INTO {table_name} ({columns}) VALUES
        {',\n'.join(values_sql)}
        """
        print(f"Inserting batch of {len(batch)} records...")
        cursor.execute(query)


def insert_into_iceberg():
    
    conn = connect(
        host="trino",
        port=8080,
        user="admin",
        catalog="iceberg",
    )
    cursor = conn.cursor()
    
    print("Creating schema if not exists...")
    cursor.execute("CREATE SCHEMA IF NOT EXISTS iceberg.single_family")

    print("Reading schema from Parquet...")
    df = pd.read_parquet(PARQUET_FILE)
    schema_sql = pandas_schema_to_iceberg(df)
    print("Schema SQL:\n", schema_sql)

    print("Creating Iceberg table if not exists...")
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS iceberg.single_family.loans (
            {schema_sql}
        )
    """)
    
    print("Inserting data into Iceberg table...")
    
    insert_dataframe(cursor, df, "iceberg.single_family.loans")

    print("Insert completed.")



with DAG("single_family_pipeline", start_date=datetime(2024, 1, 1), schedule_interval=None, catchup=False) as dag:
    transform = PythonOperator(
        task_id="transform_and_upload",
        python_callable=transform_and_upload
    )

    insert = PythonOperator(
        task_id="insert_to_iceberg",
        python_callable=insert_into_iceberg
    )

    transform >> insert
