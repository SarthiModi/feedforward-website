from flask import Flask,render_template,request,redirect,url_for,session
from flask_mysqldb import MySQL
app = Flask(__name__)
app.secret_key = "supersecretkey123"  



app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'          
app.config['MYSQL_PASSWORD'] = 'Sarthi@33333' 
app.config['MYSQL_DB'] = 'surplus_food'

mysql = MySQL(app)



@app.route("/")
def home():
    return render_template("home.html")

@app.route("/donor_login",methods=['GET', 'POST'])
def donor():
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
        else:
            return "Invalid credentials. Please try again."
    return render_template("donor_login.html")

@app.route("/recipiant_login",methods=['GET', 'POST'])
def recipiant():
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
            return redirect(url_for('recipiant_dashboard'))
        else:
            return "Invalid credentials. Please try again."
    return render_template("recipiant_login.html")

@app.route("/recipiant_signin",methods=['GET', 'POST'])
def recsignin():
    if request.method == 'POST':
        name = request.form['recipientName']
        email = request.form['recipientEmail']
        password = request.form['recipientPassword']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO ressignin (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, password))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('recipiant'))
    return render_template("recipiant_signin.html")


@app.route("/donor_signin",methods=['GET', 'POST'])
def donorsignin():
    if request.method == 'POST':
        name = request.form['donorName']
        email = request.form['donorEmail']
        password = request.form['donorPassword']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO donorsignin (name, email, password) VALUES (%s, %s, %s)",
                    (name, email, password))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('donor'))
    return render_template("donor_signin.html")

@app.route('/donor_dashboard',methods=['GET', 'POST'])
def donor_dashboard():
    if 'email' not in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        food_name = request.form['foodName']
        quantity = request.form['quantity']
        expiry = request.form['expiryDate']
        address = request.form['pickupAddress']
        contact = request.form['contactNumber']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO donations (donor_email, food_name, quantity, expiry_date, pickup_address, contact_number)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (session['email'], food_name, quantity, expiry, address, contact))
        mysql.connection.commit()
        cur.close()

        return "Donation submitted successfully!"    
    return render_template("donor_dashboard.html",donor={session['name']})


@app.route('/recipiant_dashboard')
def recipiant_dashboard():
    if 'email' not in session:
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT donor_email, food_name, quantity, expiry_date, pickup_address, contact_number FROM donations")
    donations = cur.fetchall()
    cur.close()

    return render_template('recipiant_dashboard.html', donations=donations)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

