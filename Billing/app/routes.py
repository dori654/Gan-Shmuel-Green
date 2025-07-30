from flask import Blueprint, jsonify, request, send_file, render_template, redirect, url_for, flash
import mysql.connector
import os
import pandas as pd
from datetime import datetime
from db import get_db_connection 
import logging
import requests
from werkzeug.utils import secure_filename

routes = Blueprint("routes", __name__)

# Existing API routes
@routes.route('/')
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM billdb')
        users = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(users)
    except Exception:
        return {"error": "Database error"}, 500

@routes.route("/health")
def health():
    try:
        logging.info("Checking DB connection - /health endpoint")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        logging.info("DB connection is healthy")
        return "OK", 200
    except Exception as e:
        logging.exception("Health check failed: DB connection error")
        return "Failure", 500

@routes.route("/provider", methods=["POST"])
def create_provider():
    data = request.get_json()
    name = data.get("name")

    if not name:
        logging.warning("POST /provider - Missing name")
        return {"error": "Missing name"}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Provider (name) VALUES (%s)", (name,))
        conn.commit()
        provider_id = cursor.lastrowid

        logging.info(f"POST /provider - Created provider with id {provider_id}")
        return jsonify({"id": provider_id})
    
    except mysql.connector.IntegrityError:
        logging.error(f"POST /provider - Provider already exists: name='{name}'")
        return {"error": "Provider already exists"}, 400
    
    except Exception as e:
        logging.exception(f"POST /provider - Database error: {e}")
        return {"error": "Database error"}, 500

@routes.route("/provider/<int:provider_id>", methods=["PUT"])
def update_provider(provider_id):
    data = request.get_json()
    name = data.get("name")

    if not name:
        logging.warning(f"PUT /provider/{provider_id} - Missing name")
        return {"error": "Missing name"}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Provider SET name=%s WHERE id=%s", (name, provider_id))
        conn.commit()

        logging.info(f"PUT /provider/{provider_id} - Updated name to '{name}'")
        return {"message": "Updated"}

    except Exception as e:
        logging.exception(f"PUT /provider/{provider_id} - Database error: {e}")
        return {"error": "Database error"}, 500

@routes.route("/truck", methods=["POST"])
def create_truck():
    data = request.get_json()
    provider_id = data.get("provider")
    truck_id = data.get("id")

    logging.info(f"POST /truck - data received: {data}")

    if not provider_id or not truck_id:
        logging.warning("POST /truck - Missing data")
        return {"error": "Missing data"}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)", (truck_id, provider_id))
        conn.commit()
        logging.info(f"POST /truck - Truck {truck_id} created for provider {provider_id}")
        return jsonify({"id": truck_id})
    except mysql.connector.IntegrityError:
        logging.warning(f"POST /truck - Truck {truck_id} already exists")
        return {"error": "Truck already exists"}, 400
    except Exception as e:
        logging.exception(f"POST /truck - Database error: {e}")
        return {"error": "Database error"}, 500

@routes.route("/truck/<string:truck_id>", methods=["PUT"])
def update_truck(truck_id):
    data = request.get_json()
    provider_id = data.get("provider")

    logging.info(f"PUT /truck/{truck_id} - data received: {data}")

    if not provider_id:
        logging.warning(f"PUT /truck/{truck_id} - Missing provider id")
        return {"error": "Missing provider id"}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Trucks SET provider_id=%s WHERE id=%s", (provider_id, truck_id))
        conn.commit()
        logging.info(f"PUT /truck/{truck_id} - Updated to provider {provider_id}")
        return {"message": "Updated"}
    except Exception as e:
        logging.exception(f"PUT /truck/{truck_id} - Database error: {e}")
        return {"error": "Database error"}, 500

@routes.route("/rates", methods=["POST"])
def upload_rates():
    path = "./in/rates.xlsx"
    logging.info(f"POST /rates - Loading rates from file: {path}")
    try:
        df = pd.read_excel(path)
    except Exception as e:
        logging.exception(f"POST /rates - Failed to read Excel file: {e}")
        return {"error": "Failed to read Excel file"}, 500

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Rates")
        logging.info("POST /rates - Deleted old rates")

        for _, row in df.iterrows():
            product_id = row["Product"]
            rate = int(row["Rate"])
            scope = row["Scope"]

            if pd.isna(scope) or str(scope).strip().lower() == "all":
                scope = "All"
            else:
                scope = str(scope).strip()

            cursor.execute(
                "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
                (product_id, rate, scope)
            )
        conn.commit()
        logging.info("POST /rates - Rates uploaded successfully")
        return {"message": "Rates uploaded successfully"}
    except Exception as e:
        logging.exception(f"POST /rates - Database error: {e}")
        return {"error": "Database error"}, 500

@routes.route("/rates", methods=["GET"])
def download_rates():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Rates")
        rates = cursor.fetchall()

        logging.info(f"Fetched {len(rates)} rates from database")

        df = pd.DataFrame(rates)
        path = "./in/exported_rates.xlsx"
        df.to_excel(path, index=False)

        logging.info(f"Rates exported successfully to {path}")

        return send_file(
            path,
            as_attachment=True,
            download_name="rates.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logging.exception("Failed to generate rates file")
        return {"error": "Failed to generate rates file"}, 500
    
@routes.route("/truck/<string:truck_id>", methods=["GET"])
def get_truck_data(truck_id):
    logging.info(f"Start get_truck_data for truck_id={truck_id}")
    
    t1 = request.args.get("from")
    t2 = request.args.get("to")

    now = datetime.now().strftime("%Y%m%d%H%M%S")
    first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y%m%d%H%M%S")

    if not t1:
        t1 = first_of_month
        logging.info(f"Parameter 'from' not provided. Using first_of_month={t1}")
    if not t2:
        t2 = now
        logging.info(f"Parameter 'to' not provided. Using now={t2}")

    try:
        dt_from = datetime.strptime(t1, "%Y%m%d%H%M%S")
        dt_to = datetime.strptime(t2, "%Y%m%d%H%M%S")
    except ValueError:
        logging.warning(f"Invalid datetime format: from={t1}, to={t2}")
        return {"error": "Invalid datetime format. Use yyyymmddhhmmss"}, 400

    logging.debug(f"Parsed dates: from={dt_from}, to={dt_to}")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Trucks WHERE id = %s", (truck_id,))
    truck = cursor.fetchone()

    if not truck:
        logging.warning(f"Truck not found: {truck_id}")
        return {"error": "Truck not found"}, 404

    logging.info(f"Truck found: {truck_id}")

    cursor.execute("""
        SELECT truckTara FROM Transactions
        WHERE truck = %s AND truckTara IS NOT NULL
        ORDER BY datetime DESC
        LIMIT 1
    """, (truck_id,))
    tara_row = cursor.fetchone()
    tara = tara_row["truckTara"] if tara_row else None
    logging.info(f"Tara value: {tara}")

    cursor.execute("""
        SELECT DISTINCT session_id FROM Transactions
        WHERE truck = %s AND datetime BETWEEN %s AND %s
        ORDER BY session_id ASC
    """, (truck_id, dt_from, dt_to))
    sessions = [row["session_id"] for row in cursor.fetchall()]
    logging.info(f"Found {len(sessions)} session(s) for truck {truck_id}")

    cursor.close()
    conn.close()

    logging.info(f"Finished get_truck_data for truck_id={truck_id}")
    return jsonify({
        "id": truck_id,
        "tara": tara,
        "sessions": sessions
    })

######GET BILL#####
@routes.route('/bills/<provider_id>/')
def totalbill(provider_id):
    # 1) Parse & validate time‐window
    t1_raw = request.args.get('from', '')
    t2_raw = request.args.get('to', '')
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def parse_ts(ts, default):
        try:
            return datetime.strptime(ts, "%Y%m%d%H%M%S")
        except:
            return default

    t1 = parse_ts(t1_raw, start_of_month)
    t2 = parse_ts(t2_raw, now)

    # 2) Fetch provider name
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM Provider WHERE id=%s", (provider_id,))
    row = cursor.fetchone()

    if not row:
        logging.warning(f"Provider not found: provider_id={provider_id}")
        cursor.close(); conn.close()
        return jsonify({"error": f"Provider {provider_id} not found"}), 404
    provider_name = row[0]
    logging.info(f"Provider found: {provider_name} (ID={provider_id})")
    cursor.close(); conn.close()

    # 3) Fetch truck IDs
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Trucks WHERE provider_id=%s", (provider_id,))
    trucks = [r[0] for r in cursor.fetchall()]
    logging.info(f"{len(trucks)} trucks found for provider_id={provider_id}")
    cursor.close(); conn.close()

    # 4) Call Weight service
    payload = {
        "from":   t1.strftime("%Y%m%d%H%M%S"),
        "to":     t2.strftime("%Y%m%d%H%M%S"),
        "filter": "out"
    }
    logging.info(f"Date range: from={t1.strftime('%Y%m%d%H%M%S')} to={t2.strftime('%Y%m%d%H%M%S')}")
    product_summary = {}
    session_count  = 0

    for truck_id in trucks:
        logging.debug(f"Processing truck_id={truck_id}")
        res = requests.get("http://13.126.238.4:8082/weight", params={**payload, "truck": truck_id})
        if res.status_code != 200:
            continue
        for rec in res.json():
            if rec.get("direction") != "out":
                continue
            session_count += 1
            prod = rec["produce"]
            neto = int(rec["neto"] or 0)
            if prod not in product_summary:
                product_summary[prod] = {"product": prod, "count": 0, "amount": 0}
            product_summary[prod]["count"]  += 1
            product_summary[prod]["amount"] += neto

    # 5) Look up rates and compute pay
    conn   = get_db_connection()
    cursor = conn.cursor()
    total_pay = 0
    products  = []

    for prod, data in product_summary.items():
        # scoped rate
        cursor.execute(
            "SELECT rate FROM Rates WHERE scope=%s AND product_id=%s",
            (provider_id, prod)
        )
        row = cursor.fetchone()
        if row:
            rate = row[0]
        else:
            cursor.execute(
                "SELECT rate FROM Rates WHERE scope='ALL' AND product_id=%s",
                (prod,)
            )
            row = cursor.fetchone()
            rate = row[0] if row else 0

        pay = data["amount"] * rate
        total_pay += pay

        products.append({
            "product": prod,
            "count":   data["count"],
            "amount":  data["amount"],
            "rate":    rate,
            "pay":     pay
        })

    cursor.close(); conn.close()

    # 6) Build and return the bill JSON
    bill = {
        "id":           provider_id,
        "name":         provider_name,
        "from":         t1.strftime("%Y%m%d%H%M%S"),
        "to":           t2.strftime("%Y%m%d%H%M%S"),
        "truckCount":   len(trucks),
        "sessionCount": session_count,
        "products":     products,
        "total":        total_pay
    }
    logging.info(f"Successfully generated bill for provider_id={provider_id}")
    return jsonify(bill), 200

# ===== UI ROUTES =====

@routes.route('/ui/')
def index_ui():
    """Home page UI"""
    return render_template('index.html')

@routes.route('/ui/health')
def health_ui():
    """Health check UI"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()       # ← consume the result
        cursor.close()
        conn.close()
        status = "OK"
    except Exception as e:
        logging.exception("Health check failed")
        status = "Database connection failed"
    
    return render_template('health.html', status=status)

@routes.route('/ui/providers')
def providers_ui():
    """Providers list UI"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Provider ORDER BY name")
        cursor.fetchone() 
        providers = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('providers.html', providers=providers)
    except Exception as e:
        logging.exception("Error fetching providers")
        flash("Error fetching providers", "danger")
        return render_template('providers.html', providers=[])

@routes.route('/ui/providers/new', methods=['GET', 'POST'])
def provider_form():
    """Create new provider UI"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash("Provider name is required", "danger")
            return render_template('providers_form.html')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Provider (name) VALUES (%s)", (name,))
            conn.commit()
            cursor.close()
            conn.close()
            flash(f"Provider '{name}' created successfully", "success")
            return redirect(url_for('routes.providers_ui'))
        except mysql.connector.IntegrityError:
            flash("Provider already exists", "danger")
        except Exception as e:
            logging.exception("Error creating provider")
            flash("Error creating provider", "danger")
    
    return render_template('providers_form.html')

@routes.route('/ui/trucks')
def trucks_ui():
    """Trucks list UI"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, p.name 
            FROM Trucks t 
            JOIN Provider p ON t.provider_id = p.id 
            ORDER BY t.id
        """)
        trucks = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('trucks.html', trucks=trucks)
    except Exception as e:
        logging.exception("Error fetching trucks")
        flash("Error fetching trucks", "danger")
        return render_template('trucks.html', trucks=[])

@routes.route('/ui/trucks/new', methods=['GET', 'POST'])
def truck_form():
    """Create new truck UI"""
    if request.method == 'POST':
        truck_id = request.form.get('truck_id', '').strip()
        provider_id = request.form.get('provider_id')
        
        if not truck_id or not provider_id:
            flash("Truck plate and provider are required", "danger")
            return redirect(url_for('routes.truck_form'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)", 
                         (truck_id, provider_id))
            conn.commit()
            cursor.close()
            conn.close()
            flash(f"Truck '{truck_id}' registered successfully", "success")
            return redirect(url_for('routes.trucks_ui'))
        except mysql.connector.IntegrityError:
            flash("Truck already exists", "danger")
        except Exception as e:
            logging.exception("Error creating truck")
            flash("Error registering truck", "danger")
    
    # Get providers for dropdown
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Provider ORDER BY name")
        providers = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        logging.exception("Error fetching providers")
        providers = []
        flash("Error fetching providers", "danger")
    
    return render_template('truck_form.html', providers=providers)

@routes.route('/ui/rates', methods=['GET', 'POST'])
def rates_ui():
    """Rates management UI"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file selected", "danger")
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash("No file selected", "danger")
            return redirect(request.url)
        
        if file and file.filename.endswith('.xlsx'):
            try:
                # Save uploaded file
                filename = secure_filename(file.filename)
                filepath = os.path.join('./in', 'rates.xlsx')
                os.makedirs('./in', exist_ok=True)
                file.save(filepath)
                
                # Process the file
                df = pd.read_excel(filepath)
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Rates")
                
                for _, row in df.iterrows():
                    product_id = row["Product"]
                    rate = int(row["Rate"])
                    scope = row["Scope"]
                    
                    if pd.isna(scope) or str(scope).strip().lower() == "all":
                        scope = "All"
                    else:
                        scope = str(scope).strip()
                    
                    cursor.execute(
                        "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
                        (product_id, rate, scope)
                    )
                
                conn.commit()
                cursor.close()
                conn.close()
                flash("Rates uploaded successfully", "success")
                
            except Exception as e:
                logging.exception("Error uploading rates")
                flash("Error uploading rates file", "danger")
        else:
            flash("Please upload an Excel (.xlsx) file", "danger")
    
    # Get existing files
    files = []
    try:
        if os.path.exists('./in'):
            files = [f for f in os.listdir('./in') if f.endswith('.xlsx')]
    except Exception as e:
        logging.exception("Error listing files")
    
    # Handle download requests
    download_file = request.args.get('download')
    if download_file:
        try:
            filepath = os.path.join('./in', secure_filename(download_file))
            if os.path.exists(filepath):
                return send_file(filepath, as_attachment=True)
            else:
                flash("File not found", "danger")
        except Exception as e:
            logging.exception("Error downloading file")
            flash("Error downloading file", "danger")
    
    return render_template('rates.html', files=files)

@routes.route('/ui/bills', methods=['GET', 'POST'])
def bills_ui():
    """Bills generation UI"""
    bill = None
    
    if request.method == 'POST':
        provider_id = request.form.get('provider_id')
        from_date = request.form.get('from', '').strip()
        to_date = request.form.get('to', '').strip()
        
        if not provider_id:
            flash("Please select a provider", "danger")
            return redirect(request.url)
        
        try:
            # Use the existing bill generation logic
            now = datetime.now()
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            def parse_ts(ts, default):
                try:
                    return datetime.strptime(ts, "%Y%m%d%H%M%S")
                except:
                    return default
            
            t1 = parse_ts(from_date, start_of_month)
            t2 = parse_ts(to_date, now)
            
            # Fetch provider name
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM Provider WHERE id=%s", (provider_id,))
            row = cursor.fetchone()
            
            if not row:
                flash("Provider not found", "danger")
                cursor.close()
                conn.close()
                return redirect(request.url)
            
            provider_name = row[0]
            cursor.close()
            conn.close()
            
            # Fetch truck IDs
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Trucks WHERE provider_id=%s", (provider_id,))
            trucks = [r[0] for r in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            # Call Weight service and process data (same logic as API)
            payload = {
                "from": t1.strftime("%Y%m%d%H%M%S"),
                "to": t2.strftime("%Y%m%d%H%M%S"),
                "filter": "out"
            }
            
            product_summary = {}
            session_count = 0
            
            for truck_id in trucks:
                try:
                    res = requests.get("http://13.126.238.4:8082/weight", 
                                     params={**payload, "truck": truck_id})
                    if res.status_code != 200:
                        continue
                    for rec in res.json():
                        if rec.get("direction") != "out":
                            continue
                        session_count += 1
                        prod = rec["produce"]
                        neto = int(rec["neto"] or 0)
                        if prod not in product_summary:
                            product_summary[prod] = {"product": prod, "count": 0, "amount": 0}
                        product_summary[prod]["count"] += 1
                        product_summary[prod]["amount"] += neto
                except Exception as e:
                    logging.exception(f"Error fetching data for truck {truck_id}")
                    continue
            
            # Look up rates and compute pay
            conn = get_db_connection()
            cursor = conn.cursor()
            total_pay = 0
            products = []
            
            for prod, data in product_summary.items():
                # scoped rate
                cursor.execute(
                    "SELECT rate FROM Rates WHERE scope=%s AND product_id=%s",
                    (provider_id, prod)
                )
                row = cursor.fetchone()
                if row:
                    rate = row[0]
                else:
                    cursor.execute(
                        "SELECT rate FROM Rates WHERE scope='ALL' AND product_id=%s",
                        (prod,)
                    )
                    row = cursor.fetchone()
                    rate = row[0] if row else 0
                
                pay = data["amount"] * rate
                total_pay += pay
                
                products.append({
                    "product": prod,
                    "count": data["count"],
                    "amount": data["amount"],
                    "rate": rate,
                    "pay": pay
                })
            
            cursor.close()
            conn.close()
            
            # Build bill object for template
            bill = {
                "id": provider_id,
                "name": provider_name,
                "from": t1.strftime("%Y%m%d%H%M%S"),
                "to": t2.strftime("%Y%m%d%H%M%S"),
                "truckCount": len(trucks),
                "sessionCount": session_count,
                "products": products,
                "total": total_pay
            }
            
            flash("Bill generated successfully", "success")
            
        except Exception as e:
            logging.exception("Error generating bill")
            flash("Error generating bill", "danger")
    
    # Get providers for dropdown
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Provider ORDER BY name")
        providers = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        logging.exception("Error fetching providers")
        providers = []
        flash("Error fetching providers", "danger")
    
    return render_template('bills.html', providers=providers, bill=bill)