from flask import Flask, render_template, request, session, redirect
from bs4 import BeautifulSoup
from passlib.hash import sha256_crypt
from flask_pymongo import PyMongo
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['MONGO_URI'] = 'mongodb://localhost:27017/'
mongo = PyMongo(app)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.43'
}


def flipkart(name):
    try:
        name1 = name.replace(" ", "+")
        flipkart_url = f'https://www.flipkart.com/search?q={name1}&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=off&as=off'
        res = requests.get(flipkart_url, headers=headers)

        print("\nSearching in Flipkart....")
        soup = BeautifulSoup(res.text, 'html.parser')

        if soup.select('._4rR01T'):
            flipkart_name = soup.select('._4rR01T')[0].getText().strip()
            if name.upper() in flipkart_name.upper():
                flipkart_price = soup.select('._30jeq3')[0].getText().strip()
                return flipkart_name, flipkart_price, flipkart_url

        elif soup.select('.s1Q9rs'):
            flipkart_name = soup.select('.s1Q9rs')[0].getText().strip()
            if name.upper() in flipkart_name.upper():
                flipkart_price = soup.select('._30jeq3')[0].getText().strip()
                return flipkart_name, flipkart_price, flipkart_url

        return None, '0', None
    except:
        return None, '0', None


def amazon(name):
    try:
        name1 = name.replace(" ", "-")
        name2 = name.replace(" ", "+")
        amazon_url = f'https://www.amazon.in/{name1}/s?k={name2}'
        res = requests.get(amazon_url, headers=headers)

        print("\nSearching in Amazon...")
        soup = BeautifulSoup(res.text, 'html.parser')
        amazon_page = soup.select('.a-color-base.a-text-normal')
        amazon_page_length = len(amazon_page)
        for i in range(amazon_page_length):
            name = name.upper()
            amazon_name = soup.select('.a-color-base.a-text-normal')[i].getText().strip()
            if name in amazon_name.upper():
                amazon_price = soup.select('.a-price-whole')[i].getText().strip()
                return amazon_name, amazon_price, amazon_url


        return None, '0', None
    except:
        return None, '0', None


def convert(price):
    price = price.replace(" ", "").replace("INR", "").replace(",", "").replace("₹", "")
    return int(float(price))


# Function to check if a user exists in the MongoDB collection
def user_exists(email_or_mobile):
    user_collection = mongo.db.users
    user = user_collection.find_one({"email_or_mobile": email_or_mobile})
    return user is not None

# Function to retrieve a user's hashed password from the MongoDB collection
def get_user_password(email_or_mobile):
    user_collection = mongo.db.users
    user = user_collection.find_one({"email_or_mobile": email_or_mobile})
    return user['password'] if user else None

# Function to save a new user's information to the MongoDB collection
def save_user(name, email_or_mobile, hashed_password):
    user_collection = mongo.db.users
    user = {
        "name": name,
        "email_or_mobile": email_or_mobile,
        "password": hashed_password
    }
    user_collection.insert_one(user)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        return render_template('results.html', product_name=product_name)
    return render_template('index.html')

@app.route('/results')
def results():
    if 'email_or_mobile' not in session:
        return redirect('/signin')

    product_name = request.args.get('product_name')
    flipkart_name, flipkart_price, flipkart_url = flipkart(product_name)
    amazon_name, amazon_price, amazon_url = amazon(product_name)

    if flipkart_name is None:
        flipkart_name = "No product found!"
        flipkart_price = '0'
        flipkart_url = None
    else:
        flipkart_price = convert(flipkart_price)

    if amazon_name is None:
        amazon_name = "No product found!"
        amazon_price = '0'
        amazon_url = None
    else:
        amazon_price = convert(amazon_price)

    price_difference = flipkart_price - amazon_price

    # Determine which website is more affordable
    if flipkart_price == 0 and amazon_price == 0:
        affordable_website = "No product found!"
    elif flipkart_price == 0:
        affordable_website = "Amazon"
    elif amazon_price == 0:
        affordable_website = "Flipkart"
    elif flipkart_price < amazon_price:
        affordable_website = "Flipkart"
    else:
        affordable_website = "Amazon"

    return render_template('results.html', flipkart_name=flipkart_name, flipkart_price=flipkart_price,
                           amazon_name=amazon_name, amazon_price=amazon_price, affordable_website=affordable_website,
                           flipkart_url=flipkart_url, amazon_url=amazon_url)

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if 'email_or_mobile' in session:
        return redirect('/promo')

    if request.method == 'POST':
        email_or_mobile = request.form['email_or_mobile']
        password = request.form['password']

        if user_exists(email_or_mobile):
            hashed_password = get_user_password(email_or_mobile)
            if sha256_crypt.verify(password, hashed_password):
                session['email_or_mobile'] = email_or_mobile
                return redirect('/results')
            else:
                error_message = 'Incorrect password. Please try again.'
        else:
            error_message = 'User does not exist. Please register.'

        return render_template('signin.html', error_message=error_message)

    return render_template('signin.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'email_or_mobile' in session:
        return redirect('/results')

    if request.method == 'POST':
        name = request.form['name']
        email_or_mobile = request.form['email_or_mobile']
        password = request.form['password']

        hashed_password = sha256_crypt.hash(password)
        save_user(name, email_or_mobile, hashed_password)

        session['email_or_mobile'] = email_or_mobile
        return redirect('/results')
    return render_template('register.html')


if __name__ == '__main__':
    app.run(debug=True)
