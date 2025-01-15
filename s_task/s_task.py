from flask import Flask, render_template, url_for, redirect, request, flash, abort
from itsdangerous import URLSafeSerializer, SignatureExpired, BadSignature
from peewee import *
import pandas as pd
import os 
import sqlite3
from werkzeug.utils import secure_filename

def tableCheck(conn, tab_name) :
   query = f"""SELECT name FROM sqlite_master 
   WHERE type='table' AND name='{tab_name}'
   """
   conn.execute(query)
   return conn.fetchone() is not None 

def createTable() :
   db = sqlite3.connect('cars.db')
   dbCursor = db.cursor()

   if not(tableCheck(dbCursor, 'cars')) :
      query = """
         CREATE TABLE cars (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         brand VARCHAR NOT NULL,
         type VARCHAR NOT NULL,
         price INTEGER NOT NULL
         )
      """
      dbCursor.execute(query)
      return True
   else :
      return False

if createTable() == True:
   print('Berhasil membuat Table')

app = Flask(__name__)
app.secret_key = 'carslist'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx'}

secKey = URLSafeSerializer(app.secret_key)

def dbConn() :
   db = sqlite3.connect('cars.db')
   db.row_factory = sqlite3.Row
   return db

def verify_secure_url(token):
   try:
      params = secKey.loads(token)
      return params
   except SignatureExpired:
      abort(403, description="Token expired")
   except BadSignature:
      abort(403, description="Invalid token")

@app.route('/', methods = ["GET", "POST"])
def index():
   showData = []
   conn = dbConn()

   if request.method == "POST" :
      search = request.form['search']
      datas = conn.execute(f"SELECT * FROM cars WHERE brand LIKE '%{search}%' OR type LIKE '%{search}%'").fetchall()
   else :
      datas = conn.execute("SELECT * FROM cars").fetchall()

   for data in datas :
      id = secKey.dumps(data['id'])
      showData.append((id, data['brand'], data['type'], data['price']))

   conn.close()

   return render_template('index.html', rows = showData)

@app.route('/add', methods = ["GET", "POST"])
def addCars() :
   if request.method == "POST" :
      cname = request.form['cname']
      ctype = request.form['ctype']
      cprice = request.form['cprice']

      if cname != '' and ctype != '' and cprice != '' :
         conn = dbConn()
         conn.execute(
            """
            INSERT INTO cars (brand, type, price) VALUES (
            ?, ?, ?
            )
            """, (cname, ctype, cprice)
         )
         conn.commit()
         conn.close()
         flash('Data Mobil Berhasil ditambahkan', 'success')
         return redirect(url_for('index'))
      else :
         flash('Data Mobil Gagal ditambahkan', 'failed')

   return render_template('addCars.html')

@app.route('/edit/<id>', methods = ["GET", "POST"])
def editCars(id) :
   conn = dbConn()
   params = verify_secure_url(id)
   dataVal = []

   data = conn.execute(f"SELECT * FROM cars WHERE id = {params}").fetchone()

   if request.method == "POST" :
      params =  verify_secure_url(id)
      cname = request.form['cname']
      ctype = request.form['ctype']
      cprice = request.form['cprice']

      if cname != '' and ctype != '' and cprice != '' :
         conn = dbConn()
         conn.execute(
            f"""
            UPDATE cars SET 
            brand = ?, 
            type = ?, 
            price = ? 
            WHERE id = ?
            """, (cname, ctype, cprice, params)
         )
         conn.commit()
         conn.close()
         flash('Data Mobil Berhasil diubah', 'success')
         return redirect(url_for('index'))
      else :
         flash('Data Mobil Gagal diubah', 'failed')

   return render_template('editCars.html', row = [data, id])

@app.route('/delete/<id>')
def delete(id) :
   # id = int(id)
   id = verify_secure_url(id)
   conn = dbConn()
   conn.execute(f"DELETE FROM cars WHERE id = {id}")
   conn.commit()
   conn.close()

   flash('Data Mobil Berhasil Dihapus', 'delsuccess')
   return redirect(url_for('index'))

@app.route('/upload', methods = ["GET", "POST"])
def uploadsFile() :
   # Create the uploads directory if it doesn't exist
   os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

   if request.method == 'POST':
      file = request.files['fileUp']
      if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            print(file_path)

            # Memproses file berdasarkan extensi - nya
            if filename.endswith('.csv'):
               process_csv(file_path)
            elif filename.endswith('.xlsx'):
               process_xls(file_path)

            return redirect(url_for('index'))

   return render_template('uploads.html')

def allowed_file(filename):
   return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_csv(file_path):
   conn = dbConn()
   df = pd.read_csv(file_path)

   for index, row in df.iterrows():
      brand = row['brand']
      cartype = row['model']
      price = row['price']

      conn.execute("""
         INSERT INTO cars (brand, type, price)
         VALUES (?, ?, ?)
      """, (brand, cartype, price))
   
   conn.commit()
   conn.close()

def process_xls(file_path):
   conn = dbConn()
   df = pd.read_excel(file_path)

   for index, row in df.iterrows():
      brand = row['brand']
      cartype = row['model']
      price = row['price']

      conn.execute("""
         INSERT INTO cars (brand, type, price)
         VALUES (?, ?, ?)
      """, (brand, cartype, price))
   
   conn.commit()
   conn.close()

app.run(debug=True)