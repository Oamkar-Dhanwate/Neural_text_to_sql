"""
Step 2: Synthetic Data Generation Script
Populates all schemas with realistic data (500-1000 rows per table).
Run AFTER setup_db.py: python generate_data.py
"""
import psycopg2
import os
import random
import hashlib
from datetime import datetime, timedelta
from faker import Faker
from dotenv import load_dotenv

load_dotenv("../backend/.env")

DATABASE_URL = os.getenv("NEON_DATABASE_URL", "postgresql://postgres:password@localhost/text2sql")
fake = Faker()
Faker.seed(42)
random.seed(42)

# ─────────────────────────────────────────────
#  ECOMMERCE DATA
# ─────────────────────────────────────────────

CATEGORIES = [
    (1, "Electronics", None),
    (2, "Clothing", None),
    (3, "Books", None),
    (4, "Home & Garden", None),
    (5, "Sports", None),
    (6, "Smartphones", 1),
    (7, "Laptops", 1),
    (8, "Men's Clothing", 2),
    (9, "Women's Clothing", 2),
    (10, "Fiction", 3),
]

ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]


def generate_ecommerce(cur, n_customers=700, n_products=300, n_orders=1000):
    print("  → Inserting categories...")
    for cat in CATEGORIES:
        cur.execute(
            "INSERT INTO ecommerce.categories (id, name, parent_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            cat
        )

    print(f"  → Inserting {n_customers} customers...")
    customer_ids = []
    for _ in range(n_customers):
        cur.execute(
            """INSERT INTO ecommerce.customers
               (first_name, last_name, email, phone, city, country, created_at, is_active)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (
                fake.first_name(), fake.last_name(),
                fake.unique.email(),
                fake.phone_number()[:20],
                fake.city(), fake.country_code(),
                fake.date_time_between(start_date="-3y"),
                random.random() > 0.05,
            )
        )
        customer_ids.append(cur.fetchone()[0])

    print(f"  → Inserting {n_products} products...")
    product_ids = []
    for _ in range(n_products):
        cat_id = random.choice([c[0] for c in CATEGORIES if c[2] is not None] + [1, 2, 3])
        cur.execute(
            """INSERT INTO ecommerce.products
               (name, sku, category_id, price, stock_quantity, description, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (
                fake.catch_phrase()[:199],
                fake.unique.bothify("SKU-####-???"),
                cat_id,
                round(random.uniform(5, 1500), 2),
                random.randint(0, 500),
                fake.text(max_nb_chars=200),
                fake.date_time_between(start_date="-2y"),
            )
        )
        product_ids.append(cur.fetchone()[0])

    print(f"  → Inserting {n_orders} orders + items...")
    for _ in range(n_orders):
        cid = random.choice(customer_ids)
        status = random.choices(ORDER_STATUSES, weights=[5, 10, 20, 60, 5])[0]
        created = fake.date_time_between(start_date="-2y")
        cur.execute(
            """INSERT INTO ecommerce.orders
               (customer_id, status, shipping_address, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (cid, status, fake.address(), created, created + timedelta(days=random.randint(1, 10)))
        )
        order_id = cur.fetchone()[0]

        total = 0.0
        n_items = random.randint(1, 5)
        for _ in range(n_items):
            pid = random.choice(product_ids)
            cur.execute("SELECT price FROM ecommerce.products WHERE id = %s", (pid,))
            price = float(cur.fetchone()[0])
            qty = random.randint(1, 4)
            cur.execute(
                """INSERT INTO ecommerce.order_items (order_id, product_id, quantity, unit_price)
                   VALUES (%s,%s,%s,%s)""",
                (order_id, pid, qty, price)
            )
            total += price * qty

        cur.execute("UPDATE ecommerce.orders SET total_amount=%s WHERE id=%s", (round(total, 2), order_id))

    print("  → Inserting reviews...")
    for _ in range(800):
        cur.execute(
            """INSERT INTO ecommerce.reviews (product_id, customer_id, rating, title, body, created_at)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (
                random.choice(product_ids),
                random.choice(customer_ids),
                random.randint(1, 5),
                fake.sentence(nb_words=6)[:199],
                fake.paragraph(),
                fake.date_time_between(start_date="-1y"),
            )
        )


# ─────────────────────────────────────────────
#  FINANCE DATA
# ─────────────────────────────────────────────

ACCOUNT_TYPES = ["checking", "savings", "money_market", "cd"]
TRANSACTION_TYPES = ["debit", "credit", "transfer", "fee"]
LOAN_TYPES = ["personal", "mortgage", "auto", "student", "business"]
MERCHANT_CATEGORIES = ["groceries", "restaurants", "utilities", "entertainment", "healthcare", "retail"]


def generate_finance(cur, n_customers=600, n_branches=20):
    print("  → Inserting finance customers...")
    customer_ids = []
    for _ in range(n_customers):
        dob = fake.date_of_birth(minimum_age=18, maximum_age=80)
        cur.execute(
            """INSERT INTO finance.customers
               (first_name, last_name, email, ssn_hash, date_of_birth, credit_score, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (
                fake.first_name(), fake.last_name(),
                fake.unique.email(),
                hashlib.sha256(fake.ssn().encode()).hexdigest(),
                dob,
                random.randint(300, 850),
                fake.date_time_between(start_date="-5y"),
            )
        )
        customer_ids.append(cur.fetchone()[0])

    print("  → Inserting branches...")
    branch_ids = []
    for _ in range(n_branches):
        cur.execute(
            """INSERT INTO finance.branches (name, city, state, address, phone)
               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (
                f"{fake.company()} Branch",
                fake.city(), fake.state_abbr(),
                fake.address(), fake.phone_number()[:20],
            )
        )
        branch_ids.append(cur.fetchone()[0])

    print("  → Inserting accounts + transactions...")
    account_ids = []
    for cid in customer_ids:
        n_accs = random.randint(1, 3)
        for _ in range(n_accs):
            cur.execute(
                """INSERT INTO finance.accounts
                   (customer_id, branch_id, account_type, balance, currency, status, opened_at)
                   VALUES (%s,%s,%s,%s,'USD',%s,%s) RETURNING id""",
                (
                    cid, random.choice(branch_ids),
                    random.choice(ACCOUNT_TYPES),
                    round(random.uniform(100, 100000), 2),
                    "active" if random.random() > 0.05 else "closed",
                    fake.date_time_between(start_date="-4y"),
                )
            )
            account_ids.append(cur.fetchone()[0])

    # Generate transactions
    for _ in range(3000):
        acc_id = random.choice(account_ids)
        amount = round(random.uniform(1, 5000), 2)
        cur.execute(
            """INSERT INTO finance.transactions
               (account_id, transaction_type, amount, description, merchant, category, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (
                acc_id,
                random.choice(TRANSACTION_TYPES),
                amount,
                fake.sentence(nb_words=5),
                fake.company()[:199],
                random.choice(MERCHANT_CATEGORIES),
                fake.date_time_between(start_date="-2y"),
            )
        )

    print("  → Inserting loans + payments...")
    for cid in random.sample(customer_ids, min(300, len(customer_ids))):
        cur.execute(
            """INSERT INTO finance.loans
               (customer_id, loan_type, principal, interest_rate, term_months, status, disbursed_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (
                cid,
                random.choice(LOAN_TYPES),
                round(random.uniform(1000, 500000), 2),
                round(random.uniform(0.03, 0.25), 4),
                random.choice([12, 24, 36, 60, 120, 180, 360]),
                random.choice(["active", "paid_off", "defaulted"]),
                fake.date_time_between(start_date="-3y"),
            )
        )
        loan_id = cur.fetchone()[0]
        for _ in range(random.randint(3, 24)):
            cur.execute(
                """INSERT INTO finance.payments (loan_id, amount, payment_date, is_on_time)
                   VALUES (%s,%s,%s,%s)""",
                (
                    loan_id,
                    round(random.uniform(100, 3000), 2),
                    fake.date_between(start_date="-3y"),
                    random.random() > 0.1,
                )
            )


# ─────────────────────────────────────────────
#  HEALTHCARE DATA
# ─────────────────────────────────────────────

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
SPECIALIZATIONS = ["Cardiology", "Neurology", "Orthopedics", "Pediatrics", "Oncology", "Dermatology", "Psychiatry", "General Practice"]
SEVERITY_LEVELS = ["mild", "moderate", "severe", "critical"]
BILLING_STATUSES = ["pending", "paid", "partial", "waived"]


def generate_healthcare(cur, n_patients=800, n_doctors=50):
    print("  → Inserting patients...")
    patient_ids = []
    for _ in range(n_patients):
        cur.execute(
            """INSERT INTO healthcare.patients
               (first_name, last_name, date_of_birth, gender, blood_type, phone, city, registered_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (
                fake.first_name(), fake.last_name(),
                fake.date_of_birth(minimum_age=0, maximum_age=90),
                random.choice(["male", "female", "other"]),
                random.choice(BLOOD_TYPES),
                fake.phone_number()[:20],
                fake.city(),
                fake.date_time_between(start_date="-5y"),
            )
        )
        patient_ids.append(cur.fetchone()[0])

    print("  → Inserting doctors...")
    doctor_ids = []
    for _ in range(n_doctors):
        spec = random.choice(SPECIALIZATIONS)
        cur.execute(
            """INSERT INTO healthcare.doctors
               (first_name, last_name, specialization, license_number, department, email, years_experience)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (
                fake.first_name(), fake.last_name(),
                spec,
                fake.unique.bothify("LIC-#####"),
                spec,
                fake.unique.email(),
                random.randint(1, 35),
            )
        )
        doctor_ids.append(cur.fetchone()[0])

    print("  → Inserting appointments + diagnoses + prescriptions + billing...")
    for _ in range(2000):
        pid = random.choice(patient_ids)
        did = random.choice(doctor_ids)
        appt_date = fake.date_time_between(start_date="-2y")
        status = random.choices(["scheduled", "completed", "cancelled", "no_show"], weights=[10, 70, 15, 5])[0]

        cur.execute(
            """INSERT INTO healthcare.appointments
               (patient_id, doctor_id, appointment_date, status, reason, notes, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (pid, did, appt_date, status, fake.sentence(), fake.text(max_nb_chars=150), appt_date)
        )
        appt_id = cur.fetchone()[0]

        if status == "completed":
            # Diagnosis
            cur.execute(
                """INSERT INTO healthcare.diagnoses
                   (appointment_id, icd_code, diagnosis_name, severity, notes)
                   VALUES (%s,%s,%s,%s,%s)""",
                (
                    appt_id,
                    fake.bothify("?##.#"),
                    fake.bs()[:199],
                    random.choice(SEVERITY_LEVELS),
                    fake.sentence(),
                )
            )
            # Prescriptions
            for _ in range(random.randint(0, 3)):
                cur.execute(
                    """INSERT INTO healthcare.prescriptions
                       (appointment_id, medication_name, dosage, frequency, duration_days, notes)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (
                        appt_id,
                        fake.word().capitalize() + "cin",
                        f"{random.randint(5, 500)}mg",
                        random.choice(["once daily", "twice daily", "as needed", "every 8 hours"]),
                        random.choice([7, 14, 30, 60, 90]),
                        fake.sentence() if random.random() > 0.5 else None,
                    )
                )
            # Billing
            amount = round(random.uniform(50, 5000), 2)
            covered = round(amount * random.uniform(0, 0.9), 2)
            cur.execute(
                """INSERT INTO healthcare.billing
                   (appointment_id, amount, insurance_covered, patient_paid, status, billed_at)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (
                    appt_id, amount, covered,
                    round(amount - covered, 2),
                    random.choice(BILLING_STATUSES),
                    appt_date + timedelta(days=random.randint(1, 7)),
                )
            )


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    print("🔌 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True  # Changed to True
    cur = conn.cursor()

    try:
        print("\n📦 Generating ECOMMERCE data...")
        generate_ecommerce(cur)
        conn.commit()
        print("  ✅ Ecommerce data committed")

        print("\n💰 Generating FINANCE data...")
        generate_finance(cur)
        conn.commit()
        print("  ✅ Finance data committed")

        print("\n🏥 Generating HEALTHCARE data...")
        generate_healthcare(cur)
        conn.commit()
        print("  ✅ Healthcare data committed")

        print("\n🎉 All synthetic data generated successfully!")

    except Exception as e:
        if not conn.closed:  # Added check to prevent InterfaceError
            conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()