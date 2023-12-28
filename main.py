from flask import *
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename
from flask import Flask,render_template,request
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///base.db'
app.config["SECRET_KEY"] = "SOME VAL"
db = SQLAlchemy(app)

# входиv в контекст приложения
with app.app_context():
    # cоздание таблиц в контексте приложения
    db.create_all()

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def getLoginDetails():
    with sqlite3.connect('base.db') as conn:
        cur = conn.cursor()
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
        else:
            loggedIn = True
            cur.execute("SELECT userId, firstName FROM users WHERE email = '" + session['email'] + "'")
            userId, firstName = cur.fetchone()
            cur.execute("SELECT count(productId) FROM kart WHERE userId = " + str(userId))
            noOfItems = cur.fetchone()[0]
    conn.close()
    return (loggedIn, firstName, noOfItems)

@app.route("/")
def root():
    loggedIn, firstName, noOfItems = getLoginDetails()
    with sqlite3.connect('base.db') as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name, price, description, image, stock FROM products')
        itemData = cur.fetchall()
        cur.execute('SELECT categoryId, name FROM categories')
        categoryData = cur.fetchall()
    itemData = parse(itemData)   
    return render_template('index.html', itemData=itemData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryData=categoryData)

@app.route("/loginForm")
def loginForm():
    if 'email' in session:
        return redirect(url_for('root'))
    else:
        return render_template('login.html', error='')

@app.route("/login", methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if is_valid(email, password):
            session['email'] = email
            if email == 'admin@root.ru':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('root'))
        else:
            return "invalid ok va"
    return render_template('login.html')

def is_valid(email, password):
    con = sqlite3.connect('base.db')
    cur = con.cursor()
    cur.execute('SELECT email, password FROM users')
    data = cur.fetchall()
    for row in data:
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            return True
    return False
@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        #Parse form data    
        password = request.form['password']
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']

        with sqlite3.connect('base.db') as con:
            try:
                cur = con.cursor()
                cur.execute('INSERT INTO users (password, email, firstName, lastName) VALUES (?, ?, ?, ?)', (hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName))

                con.commit()

                msg = "Registered Successfully"
            except:
                con.rollback()
                msg = "Error occured"
        con.close()
        return render_template("login.html", error=msg)

@app.route("/registerationForm")
def registrationForm():
    return render_template("register.html")
@app.route("/add")
def admin():
    with sqlite3.connect('base.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT categoryId, name FROM categories")
        categories = cur.fetchall()
    conn.close()
    return render_template('add.html', categories=categories)

@app.route("/addItem", methods=["GET", "POST"])
def addItem():
    if request.method == "POST":
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        categoryId = int(request.form['category'])

        #Uploading image procedure
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        imagename = filename
        with sqlite3.connect('base.db') as conn:
            try:
                cur = conn.cursor()
                cur.execute('''INSERT INTO products (name, price, description, image, categoryId) VALUES (?, ?, ?, ?, ?)''', (name, price, description, imagename, categoryId))
                conn.commit()
                msg="added successfully"
            except:
                msg="error occured"
                conn.rollback()
        conn.close()
        print(msg)
        return redirect(url_for('root'))

@app.route("/remove")
def remove():
    with sqlite3.connect('base.db') as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name, price, description FROM products')
        data = cur.fetchall()
    conn.close()
    return render_template('remove.html', data=data)

@app.route("/removeItem")
def removeItem():
    productId = request.args.get('productId')
    with sqlite3.connect('base.db') as conn:
        try:
            cur = conn.cursor()
            cur.execute('DELETE FROM products WHERE productID = ' + productId)
            conn.commit()
            msg = "Deleted successsfully"
        except:
            conn.rollback()
            msg = "Error occured"
    conn.close()
    print(msg)
    return redirect(url_for('root'))
@app.route("/displayCategory")
def displayCategory():
        loggedIn, firstName, noOfItems = getLoginDetails()
        categoryId = request.args.get("categoryId")
        with sqlite3.connect('base.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT products.productId, products.name, products.price, products.image, categories.name FROM products, categories WHERE products.categoryId = categories.categoryId AND categories.categoryId = " + categoryId)
            data = cur.fetchall()
        conn.close()
        categoryName = data[0][4]
        data = parse(data)
        return render_template('product_detail.html', data=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryName=categoryName)

@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get('productId')
    with sqlite3.connect('base.db') as conn:
        cur = conn.cursor()
        cur.execute('SELECT productId, name, price, description, image, stock FROM products WHERE productId = ' + productId)
        productData = cur.fetchone()
    conn.close()
    return render_template('aboutproduct.html', data=productData, loggedIn = loggedIn, firstName = firstName, noOfItems = noOfItems)
@app.route("/addToCart")
def addToCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    else:
        productId = int(request.args.get('productId'))
        with sqlite3.connect('base.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId FROM users WHERE email = '" + session['email'] + "'")
            userId = cur.fetchone()[0]
            try:
                # Проверяем, есть ли уже товар в корзине
                cur.execute("SELECT * FROM kart WHERE userId = ? AND productId = ?", (userId, productId))
                existing_product = cur.fetchone()

                if existing_product:
                    # Если товар уже есть, увеличиваем количество
                    cur.execute("UPDATE kart SET quantity = quantity + 1 WHERE userId = ? AND productId = ?",
                                (userId, productId))
                else:
                    # Если товара нет в корзине, добавляем его с начальным количеством 1
                    cur.execute("INSERT INTO kart (userId, productId, quantity) VALUES (?, ?, 1)", (userId, productId))

                conn.commit()
                msg = "Added successfully"
            except:
                conn.rollback()
                msg = "Error occurred"
        conn.close()
        return redirect(url_for('prodp'))


@app.route("/cart")
def cart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with sqlite3.connect('base.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
        cur.execute("SELECT products.productId, products.name, products.price, products.image, kart.quantity FROM products JOIN kart ON products.productId = kart.productId WHERE kart.userId = " + str(userId))
        products = cur.fetchall()
    totalPrice = 0
    for row in products:
        totalPrice += row[2] * (row[4] if row[4] is not None else 0)
    return render_template("kart.html", products = products, totalPrice=totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)
@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('root'))


@app.route("/removeFromCart")
def removeFromCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    email = session['email']
    productId = int(request.args.get('productId'))
    with sqlite3.connect('base.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
        userId = cur.fetchone()[0]
        try:
            cur.execute("DELETE FROM kart WHERE userId = " + str(userId) + " AND productId = " + str(productId))
            conn.commit()
            msg = "removed successfully"
        except:
            conn.rollback()
            msg = "error occured"
    conn.close()
    return redirect(url_for('cart'))
@app.route("/prod")
def prodp():
    return render_template('product.html')
@app.route("/contact")
def contac():
    loggedIn, firstName, noOfItems = getLoginDetails()
    return render_template('contact.html', loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)


@app.route("/about")
def abou():
    return render_template('about.html')
@app.route("/appoint", methods = ['GET', 'POST'])
def appoint():
    if request.method == 'POST':    
        name = request.form['name']
        phone = request.form['phonenumber']
        gender = request.form['gender']
        dname = request.form['Doctor']
        digo = request.form['digo']
        time = request.form['timing']

        with sqlite3.connect('base.db') as con:
            try:
                cur = con.cursor()
                cur.execute('INSERT INTO doctor (name,phone,gender,dname,digo,time) VALUES (?, ?, ?, ?, ?, ?)', (name,phone,gender,dname,digo,time))
                con.commit()
                msg = "added Successfully"
            except:
                con.rollback()
                msg = "Error occured"
        con.close()
        return render_template("index.html", error=msg)

@app.route("/appo")
def appoi():
    return render_template('appointment.html')
def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def parse(data):
    ans = []
    i = 0
    while i < len(data):
        curr = []
        for j in range(7):
            if i >= len(data):
                break
            curr.append(data[i])
            i += 1
        ans.append(curr)
    return ans

@app.route("/removeSelectedFromCart", methods=["POST"])
def removeSelectedFromCart():
    if 'email' not in session:
        return jsonify({"error": "User not logged in"})

    email = session['email']
    product_ids = request.json.get('productIds', [])

    with sqlite3.connect('base.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT userId FROM users WHERE email = ?", (email,))
        user_id = cur.fetchone()[0]

        for product_id in product_ids:
            cur.execute("DELETE FROM kart WHERE userId = ? AND productId = ?", (user_id, product_id))

        conn.commit()

    return jsonify({"success": True})

@app.route("/updateQuantity")
def updateQuantity():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    else:
        productId = int(request.args.get('productId'))
        action = request.args.get('action')

        with sqlite3.connect('base.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT userId FROM users WHERE email = '" + session['email'] + "'")
            userId = cur.fetchone()[0]

            if action == 'increase':
                cur.execute("SELECT COALESCE(quantity, 0) FROM kart WHERE userId = ? AND productId = ?",
                            (userId, productId))
                quantity = cur.fetchone()[0]

                cur.execute("UPDATE kart SET quantity = COALESCE(quantity, 0) + 1 WHERE userId = ? AND productId = ?",
                            (userId, productId))

            elif action == 'decrease':
                cur.execute("SELECT COALESCE(quantity, 0) FROM kart WHERE userId = ? AND productId = ?",
                            (userId, productId))
                quantity = cur.fetchone()[0]

                if quantity > 0:
                    cur.execute("UPDATE kart SET quantity = quantity - 1 WHERE userId = ? AND productId = ?",
                                (userId, productId))
                    # если меньше 0 удаляем
                    cur.execute("DELETE FROM kart WHERE userId = ? AND productId = ? AND quantity <= 0",
                                (userId, productId))

            conn.commit()
        conn.close()
        return redirect(url_for('cart'))

if __name__=='__main__':
    app.run(debug=True)


