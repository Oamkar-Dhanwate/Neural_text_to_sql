"""
Step 1: Database Setup Script
Creates PostgreSQL schemas and tables for ecommerce, finance, healthcare.
Run: python setup_db.py
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv("../backend/.env")

DATABASE_URL = os.getenv("NEON_DATABASE_URL")


SCHEMAS_SQL = {
    "ecommerce": """
        -- Ecommerce Schema
        CREATE SCHEMA IF NOT EXISTS ecommerce;

        CREATE TABLE IF NOT EXISTS ecommerce.categories (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            parent_id   INT REFERENCES ecommerce.categories(id),
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS ecommerce.customers (
            id          SERIAL PRIMARY KEY,
            first_name  VARCHAR(80) NOT NULL,
            last_name   VARCHAR(80) NOT NULL,
            email       VARCHAR(200) UNIQUE NOT NULL,
            phone       VARCHAR(20),
            city        VARCHAR(100),
            country     VARCHAR(80) DEFAULT 'US',
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            is_active   BOOLEAN DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS ecommerce.products (
            id              SERIAL PRIMARY KEY,
            name            VARCHAR(200) NOT NULL,
            sku             VARCHAR(60) UNIQUE,
            category_id     INT REFERENCES ecommerce.categories(id),
            price           NUMERIC(10,2) NOT NULL,
            stock_quantity  INT DEFAULT 0,
            description     TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS ecommerce.orders (
            id                SERIAL PRIMARY KEY,
            customer_id       INT NOT NULL REFERENCES ecommerce.customers(id),
            status            VARCHAR(30) DEFAULT 'pending'
                              CHECK (status IN ('pending','processing','shipped','delivered','cancelled')),
            total_amount      NUMERIC(12,2),
            shipping_address  TEXT,
            created_at        TIMESTAMPTZ DEFAULT NOW(),
            updated_at        TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS ecommerce.order_items (
            id          SERIAL PRIMARY KEY,
            order_id    INT NOT NULL REFERENCES ecommerce.orders(id),
            product_id  INT NOT NULL REFERENCES ecommerce.products(id),
            quantity    INT NOT NULL DEFAULT 1,
            unit_price  NUMERIC(10,2) NOT NULL,
            subtotal    NUMERIC(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
        );

        CREATE TABLE IF NOT EXISTS ecommerce.reviews (
            id          SERIAL PRIMARY KEY,
            product_id  INT NOT NULL REFERENCES ecommerce.products(id),
            customer_id INT NOT NULL REFERENCES ecommerce.customers(id),
            rating      SMALLINT CHECK (rating BETWEEN 1 AND 5),
            title       VARCHAR(200),
            body        TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_orders_customer ON ecommerce.orders(customer_id);
        CREATE INDEX IF NOT EXISTS idx_order_items_order ON ecommerce.order_items(order_id);
        CREATE INDEX IF NOT EXISTS idx_products_category ON ecommerce.products(category_id);
    """,

    "finance": """
        CREATE SCHEMA IF NOT EXISTS finance;

        CREATE TABLE IF NOT EXISTS finance.customers (
            id              SERIAL PRIMARY KEY,
            first_name      VARCHAR(80) NOT NULL,
            last_name       VARCHAR(80) NOT NULL,
            email           VARCHAR(200) UNIQUE NOT NULL,
            ssn_hash        VARCHAR(64),
            date_of_birth   DATE,
            credit_score    SMALLINT CHECK (credit_score BETWEEN 300 AND 850),
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS finance.branches (
            id       SERIAL PRIMARY KEY,
            name     VARCHAR(150) NOT NULL,
            city     VARCHAR(100),
            state    VARCHAR(50),
            address  TEXT,
            phone    VARCHAR(20)
        );

        CREATE TABLE IF NOT EXISTS finance.accounts (
            id              SERIAL PRIMARY KEY,
            customer_id     INT NOT NULL REFERENCES finance.customers(id),
            branch_id       INT REFERENCES finance.branches(id),
            account_type    VARCHAR(20) CHECK (account_type IN ('checking','savings','money_market','cd')),
            balance         NUMERIC(15,2) DEFAULT 0,
            currency        CHAR(3) DEFAULT 'USD',
            status          VARCHAR(15) DEFAULT 'active',
            opened_at       TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS finance.transactions (
            id                  SERIAL PRIMARY KEY,
            account_id          INT NOT NULL REFERENCES finance.accounts(id),
            transaction_type    VARCHAR(20) CHECK (transaction_type IN ('debit','credit','transfer','fee')),
            amount              NUMERIC(12,2) NOT NULL,
            description         TEXT,
            merchant            VARCHAR(200),
            category            VARCHAR(80),
            created_at          TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS finance.loans (
            id              SERIAL PRIMARY KEY,
            customer_id     INT NOT NULL REFERENCES finance.customers(id),
            loan_type       VARCHAR(30) CHECK (loan_type IN ('personal','mortgage','auto','student','business')),
            principal       NUMERIC(15,2) NOT NULL,
            interest_rate   NUMERIC(5,4) NOT NULL,
            term_months     INT NOT NULL,
            status          VARCHAR(20) DEFAULT 'active',
            disbursed_at    TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS finance.payments (
            id              SERIAL PRIMARY KEY,
            loan_id         INT NOT NULL REFERENCES finance.loans(id),
            amount          NUMERIC(12,2) NOT NULL,
            payment_date    DATE NOT NULL,
            is_on_time      BOOLEAN DEFAULT TRUE
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_account ON finance.transactions(account_id);
        CREATE INDEX IF NOT EXISTS idx_accounts_customer ON finance.accounts(customer_id);
    """,

    "healthcare": """
        CREATE SCHEMA IF NOT EXISTS healthcare;

        CREATE TABLE IF NOT EXISTS healthcare.patients (
            id              SERIAL PRIMARY KEY,
            first_name      VARCHAR(80) NOT NULL,
            last_name       VARCHAR(80) NOT NULL,
            date_of_birth   DATE,
            gender          VARCHAR(10) CHECK (gender IN ('male','female','other')),
            blood_type      VARCHAR(5),
            phone           VARCHAR(20),
            city            VARCHAR(100),
            registered_at   TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS healthcare.doctors (
            id                  SERIAL PRIMARY KEY,
            first_name          VARCHAR(80) NOT NULL,
            last_name           VARCHAR(80) NOT NULL,
            specialization      VARCHAR(100),
            license_number      VARCHAR(50) UNIQUE,
            department          VARCHAR(100),
            email               VARCHAR(200) UNIQUE,
            years_experience    INT
        );

        CREATE TABLE IF NOT EXISTS healthcare.appointments (
            id                  SERIAL PRIMARY KEY,
            patient_id          INT NOT NULL REFERENCES healthcare.patients(id),
            doctor_id           INT NOT NULL REFERENCES healthcare.doctors(id),
            appointment_date    TIMESTAMPTZ NOT NULL,
            status              VARCHAR(20) DEFAULT 'scheduled'
                                CHECK (status IN ('scheduled','completed','cancelled','no_show')),
            reason              TEXT,
            notes               TEXT,
            created_at          TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS healthcare.diagnoses (
            id              SERIAL PRIMARY KEY,
            appointment_id  INT NOT NULL REFERENCES healthcare.appointments(id),
            icd_code        VARCHAR(20),
            diagnosis_name  VARCHAR(200),
            severity        VARCHAR(20) CHECK (severity IN ('mild','moderate','severe','critical')),
            notes           TEXT
        );

        CREATE TABLE IF NOT EXISTS healthcare.prescriptions (
            id                  SERIAL PRIMARY KEY,
            appointment_id      INT NOT NULL REFERENCES healthcare.appointments(id),
            medication_name     VARCHAR(200) NOT NULL,
            dosage              VARCHAR(80),
            frequency           VARCHAR(80),
            duration_days       INT,
            notes               TEXT
        );

        CREATE TABLE IF NOT EXISTS healthcare.billing (
            id                  SERIAL PRIMARY KEY,
            appointment_id      INT NOT NULL REFERENCES healthcare.appointments(id),
            amount              NUMERIC(10,2) NOT NULL,
            insurance_covered   NUMERIC(10,2) DEFAULT 0,
            patient_paid        NUMERIC(10,2) DEFAULT 0,
            status              VARCHAR(20) DEFAULT 'pending'
                                CHECK (status IN ('pending','paid','partial','waived')),
            billed_at           TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_appointments_patient ON healthcare.appointments(patient_id);
        CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON healthcare.appointments(doctor_id);
    """
}


def setup_databases():
    print("🔌 Connecting to Neon PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    for schema_name, sql in SCHEMAS_SQL.items():
        print(f"📦 Creating schema: {schema_name}...")
        try:
            cur.execute(sql)
            print(f"  ✅ {schema_name} schema created")
        except Exception as e:
            print(f"  ❌ Error in {schema_name}: {e}")

    cur.close()
    conn.close()
    print("\n✅ All schemas created successfully!")


if __name__ == "__main__":
    setup_databases()