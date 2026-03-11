from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# ---------------- DATABASE CONFIG ----------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Sarthi@33333'
app.config['MYSQL_DB'] = 'surplus_food'
mysql = MySQL(app)

# ---------------- IMAGE UPLOAD CONFIG ----------------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- HELPER FUNCTIONS ----------------
def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine distance in km"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- DONOR AUTH ----------------
@app.route("/donor_login", methods=['GET', 'POST'])
def donor_login():
    if request.method == 'POST':
        email = request.form['donorEmail']
        password = request.form['donorPassword']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM donorsignin WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        cur.close()
        if user:
            session['email'] = email
            session['name'] = user[1]
            return redirect(url_for('donor_dashboard'))
        flash("Invalid credentials!", "danger")
    return render_template("donor_login.html")


@app.route("/donor_signup", methods=['GET', 'POST'])
def donor_signup():
    if request.method == 'POST':
        name = request.form['donorName']
        email = request.form['donorEmail']
        password = request.form['donorPassword']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO donorsignin (name, email, password) VALUES (%s,%s,%s)", (name, email, password))
        mysql.connection.commit()
        cur.close()
        flash("Account created successfully!", "success")
        return redirect(url_for('donor_login'))
    return render_template("donor_signup.html")

# ---------------- RECIPIENT AUTH ----------------
@app.route("/recipient_login", methods=['GET', 'POST'])
def recipient_login():
    if request.method == 'POST':
        email = request.form['recipientEmail']
        password = request.form['recipientPassword']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM ressignin WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        cur.close()
        if user:
            session['email'] = email
            session['name'] = user[1]
            return redirect(url_for('recipient_dashboard'))
        flash("Invalid credentials!", "danger")
    return render_template("recipient_login.html")


@app.route("/recipient_signup", methods=['GET', 'POST'])
def recipient_signup():
    if request.method == 'POST':
        name = request.form['recipientName']
        email = request.form['recipientEmail']
        password = request.form['recipientPassword']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO ressignin (name, email, password) VALUES (%s,%s,%s)", (name, email, password))
        mysql.connection.commit()
        cur.close()
        flash("Account created successfully!", "success")
        return redirect(url_for('recipient_login'))
    return render_template("recipient_signup.html")

# ---------------- DONOR DASHBOARD ----------------
@app.route("/donor_dashboard", methods=['GET', 'POST'])
def donor_dashboard():
    if 'email' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        food_name = request.form['foodName']
        quantity = request.form['quantity']
        expiry = request.form['expiryDate']
        address = request.form['pickupAddress']
        contact = request.form['contactNumber']
        pickup_lat = request.form.get('pickupLat') or None
        pickup_lon = request.form.get('pickupLon') or None

        image_file = request.files.get('foodImage')
        image_path = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"uploads/{filename}"

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO donations 
            (donor_email, food_name, quantity, expiry_date, pickup_address, contact_number, image_path, pickup_lat, pickup_lon)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (session['email'], food_name, quantity, expiry, address, contact, image_path, pickup_lat, pickup_lon))
        mysql.connection.commit()
        cur.close()
        flash("Donation added successfully!", "success")
        return redirect(url_for('my_donations'))

    return render_template("donor_dashboard.html", donor=session['name'])

@app.route("/view_recipients")
def view_recipients():
    cur = mysql.connection.cursor()
    cur.execute("SELECT name, email FROM ressignin")
    recipients = cur.fetchall()
    cur.close()
    return render_template("recipients_list.html", recipients=recipients)

# ---------------- MY DONATIONS (ACTIVE + HISTORY) ----------------
@app.route("/my_donations")
def my_donations():
    if 'email' not in session:
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()

    # Active donations (still available)
    cur.execute("""
        SELECT id, food_name, quantity, expiry_date, image_path
        FROM donations
        WHERE donor_email = %s
        ORDER BY id DESC
    """, (session['email'],))
    active_donations = cur.fetchall()

    # Delivered donations (from delivery_requests)
    cur.execute("""
        SELECT food_name, quantity, delivery_address, fare, status, recipient_email, image_path
        FROM delivery_requests
        WHERE donor_email = %s
        ORDER BY id DESC
    """, (session['email'],))
    delivered_donations = cur.fetchall()

    cur.close()
    return render_template("my_donations.html", 
                           active_donations=active_donations, 
                           delivered_donations=delivered_donations)


# ---------------- RECIPIENT DASHBOARD ----------------
@app.route("/recipient_dashboard")
def recipient_dashboard():
    if 'email' not in session:
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM donations WHERE expiry_date < CURDATE()")
    mysql.connection.commit()

    cur.execute("SELECT id, donor_email, food_name, quantity, expiry_date, pickup_address, contact_number, image_path FROM donations")
    donations = cur.fetchall()
    cur.close()
    return render_template("recipient_dashboard.html", donations=donations)


# ---------------- ADD TO CART ----------------
@app.route("/add_to_cart", methods=['POST'])
def add_to_cart():
    if 'email' not in session:
        return "Login required!", 403
    data = request.get_json()
    donation_id = data.get('donation_id')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM recipient_cart WHERE recipient_email=%s AND donation_id=%s", (session['email'], donation_id))
    exists = cur.fetchone()
    if exists:
        cur.close()
        return "Item already in cart!"
    cur.execute("INSERT INTO recipient_cart (recipient_email, donation_id, quantity) VALUES (%s,%s,%s)", (session['email'], donation_id, 1))
    mysql.connection.commit()
    cur.close()
    return "Item added to cart!"


# ---------------- VIEW CART ----------------
@app.route("/view_cart")
def view_cart():
    if 'email' not in session:
        return redirect(url_for('home'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT rc.id, d.food_name, d.quantity, d.donor_email, d.id, d.pickup_address
        FROM recipient_cart rc
        JOIN donations d ON rc.donation_id=d.id
        WHERE rc.recipient_email=%s
    """, (session['email'],))
    cart_items = cur.fetchall()
    cur.close()
    return render_template("cart.html", cart_items=cart_items)


# ---------------- CONFIRM ORDER ----------------

@app.route("/confirm_order/<int:cart_id>", methods=['GET', 'POST'])
def confirm_order(cart_id):
    if 'email' not in session:
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT d.id, d.pickup_address, d.pickup_lat, d.pickup_lon, d.food_name, d.quantity, d.image_path, d.donor_email
        FROM recipient_cart rc 
        JOIN donations d ON rc.donation_id=d.id 
        WHERE rc.id=%s AND rc.recipient_email=%s
    """, (cart_id, session['email']))
    row = cur.fetchone()
    if not row:
        cur.close()
        return "Invalid cart item."
    donation_id, pickup_address, donor_lat, donor_lon, food_name, quantity, image_path, donor_email = row

    if request.method == 'POST':
        delivery_choice = request.form.get('delivery_choice', 'pickup')
        delivery_address = request.form.get('delivery_address', pickup_address)
        rec_lat = request.form.get('recipient_lat')
        rec_lon = request.form.get('recipient_lon')

        distance_km = 0
        if rec_lat and rec_lon and donor_lat and donor_lon:
            distance_km = calculate_distance(float(donor_lat), float(donor_lon), float(rec_lat), float(rec_lon))
        fare = round(distance_km * 19, 2)

        # Save delivery request as Delivered (since no intermediate state)
        cur.execute("""
            INSERT INTO delivery_requests 
            (recipient_email, donation_id, donor_email, food_name, quantity, image_path, delivery_address, fare, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'Delivered')
        """, (session['email'], donation_id, donor_email, food_name, quantity, image_path, delivery_address, fare))

        # Clean up cart and active donation
        cur.execute("DELETE FROM donations WHERE id=%s", (donation_id,))
        cur.execute("DELETE FROM recipient_cart WHERE id=%s", (cart_id,))
        mysql.connection.commit()
        cur.close()

        # Return a popup confirmation HTML page
        if delivery_choice == 'delivery':
            message = f"Your delivery order has been confirmed!<br><b>Distance:</b> {round(distance_km,2)} km<br><b>Fare:</b> ₹{fare}"
        else:
            message = "Your pickup order has been confirmed!<br>Please visit the donor for collection."

        return f"""
        <html>
        <head>
            <script src='https://cdn.jsdelivr.net/npm/sweetalert2@11'></script>
            <script>
                window.onload = function() {{
                    Swal.fire({{
                        title: 'Order Confirmed ',
                        html: `{message}`,
                        icon: 'success',
                        confirmButtonText: 'OK',
                        timer: 4000,
                        timerProgressBar: true
                    }}).then(() => {{
                        window.location.href = '/recipient_dashboard';
                    }});
                }}
            </script>
        </head>
        <body></body>
        </html>
        """

    cur.close()
    return render_template("confirm_order.html", donation_id=donation_id, pickup_address=pickup_address, donor_lat=donor_lat, donor_lon=donor_lon)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.errorhandler(Exception)
def handle_error(e):
    import traceback
    return f"<pre>{traceback.format_exc()}</pre>", 500


if __name__ == "__main__":
    app.run(debug=True)
