from flask import Flask,app, redirect,render_template, session,url_for,send_from_directory,request,flash
from flask_sqlalchemy import SQLAlchemy
import json
from sqlalchemy import or_
from datetime import datetime
import mysql.connector
db = SQLAlchemy()
with open('config.json','r') as c:
    params=json.load(c)["params"]
app = Flask(__name__)
app.secret_key = 'rufy124'
if(params['local_server']):
    app.config["SQLALCHEMY_DATABASE_URI"] = params['local_uri']
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_uri']
db = SQLAlchemy(app)

dbs = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="qpay"
)
class customer(db.Model):
    account_no = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(20), nullable=False)
    Email = db.Column(db.String(50), nullable=False)
    Address = db.Column(db.String(100),nullable=False)
    phone_no = db.Column(db.Integer, unique=True, nullable=False)
    Password = db.Column(db.String(20), nullable=False)
    Balance = db.Column(db.Integer, nullable=True)
    def get_balance(self):
        # Fetch the updated balance from the database based on the account number
        customer_obj = customer.query.filter_by(account_no=self.account_no).first()
        if customer_obj:
            return customer_obj.Balance
        else:
            return None


class transaction(db.Model):
    transaction_id = db.Column(db.Integer, primary_key=True)
    from_account = db.Column(db.Integer, nullable=False)
    to_account = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(12), nullable=True)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.root_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/")
def homepage():
    return render_template('homepage.html',params=params)

@app.route("/login", methods=['GET', 'POST'])
def loginpage():
    error_message = "" 
    if request.method == 'POST':
        account = request.form['accountno']
        password = request.form['password']
        cursor = dbs.cursor()
        query = "SELECT * FROM customer WHERE account_no = %s AND Password = %s"
        values = (account, password)
        cursor.execute(query, values)
        user = cursor.fetchone()
        cursor.close()
        if user:
             session['logged_in'] = True
             session['account'] = account
             user_obj = customer.query.filter_by(account_no=user[0]).first()
             user_dict = {
                'account_no': user_obj.account_no,
                'Name': user_obj.Name,
                'Email': user_obj.Email,
                'Address': user_obj.Address,
                'phone_no': user_obj.phone_no,
                'Password': user_obj.Password,
                'Balance': user_obj.get_balance()
                }
             history = transaction.query.filter(or_(transaction.from_account == account, transaction.to_account == account)).all()[0:3]
             return render_template('dashboard.html',user=user_dict,history=history)
        else:
            error_message = "Invalid account no or password"
    return render_template('customer_login.html', params=params,error_message=error_message)

    


@app.route("/signup", methods=['GET','POST'])
def signuppage():
    if(request.method=='POST'):
        name=request.form.get('fullname')
        email=request.form.get('email')
        address=request.form.get('address')
        phone_no=request.form.get('phone')
        password=request.form.get('password')
        balance=request.form.get('balance')
        entry=customer(Name=name,Email=email,Address=address,phone_no=phone_no,Password=password,Balance=balance)
        db.session.add(entry)
        db.session.commit()     
    return render_template('signup.html',params=params)

@app.route("/payments",methods=['POST','GET'])
def paymentpage():
    if(request.method=='POST'):
        sender=request.form.get('from-account')
        receiver=request.form.get('to-account')
        amount=request.form.get('amount')
        passs=request.form.get('pass')
        sender_customer = customer.query.filter_by(account_no=sender).first()
        receiver_customer = customer.query.filter_by(account_no=receiver).first()
        
        if sender_customer is None:
            flash("Invalid sender account number", "error")
            return redirect(url_for('paymentpage'))
        
        if receiver_customer is None:
            flash("Invalid receiver account number", "error")
            return redirect(url_for('paymentpage'))
        if sender_customer.Password!=passs:
            flash("Invalid password", "error")
            return redirect(url_for('paymentpage'))

        if sender_customer.Balance < int(amount):
            flash("Insufficient balance in the sender's account", "error")
            return redirect(url_for('paymentpage'))
   
        sender_customer.Balance -= int(amount)
        db.session.commit()  
        
        receiver_customer.Balance += int(amount)
        db.session.commit() 

        entry=transaction(from_account=sender,to_account=receiver,amount=amount,date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        flash("Payment Successful", "success")  
        return redirect(url_for('paymentpage'))        
    return render_template('payments.html',params=params)

@app.route("/history")
def historypage():
    accountnu = session.get('account')
    history = transaction.query.filter(or_(transaction.from_account == accountnu, transaction.to_account == accountnu)).all()
    return render_template('transaction.html',history=history)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('loginpage'))


@app.route("/balance",methods=['POST','GET'])
def balancepage():
    if(request.method=='POST'):
        account_no=request.form.get('account-no')
        passs=request.form.get('password')
        customer_obj = customer.query.filter_by(account_no=account_no).first()
        if customer_obj is None:
            flash("Invalid acc number", "error")
            return redirect(url_for('balancepage'))
        if customer_obj.Password != passs:
            flash("Invalid password", "error")
            return redirect(url_for('balancepage'))
        return render_template('balance.html',params=customer_obj)
    return render_template('balance.html',params=params)

app.run(debug=True)