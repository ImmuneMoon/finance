import os
from pickle import NONE

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
import time

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """TODO: Show portfolio of stocks"""
    # selects the profile of the current user
    user_id = session['user_id']
    username = db.execute(
        'SELECT username FROM users WHERE id = :user_id', user_id=user_id)
    username = username[0]['username']

    # all stocks owned by the user
    index = db.execute(
        'SELECT company, symbol, total_shares FROM owned_shares WHERE user_id = :user_id', user_id=user_id)

    # users current cash balance
    cash = db.execute(
        'SELECT cash FROM users WHERE id = :user_id', user_id=user_id)
    # dict
    cash = int(cash[0]['cash'])

    # total value of all stocks and cash
    total_shares = db.execute(
        'SELECT total_shares FROM owned_shares WHERE user_id = :user_id', user_id=user_id)

    symbol = db.execute(
        'SELECT symbol FROM owned_shares WHERE user_id = :user_id', user_id=user_id)

    symbols = []
    companies = []
    curr_price = []
    # loops through values in symbols
    for i in range(len(symbol)):
        symbols.append(symbol[i]['symbol'])

    # checks to make sure stock is owned
    if symbols[0] != 'N/A':

        # loops through values in symbols
        for i in range(len(symbol)):
            # adds each company dict to the companies list after API lookup of given symbols
            companies.append(lookup(symbol[i]['symbol']))

        # loops though the companies list of dicts
        for v in range(len(companies)):
            # adds each price to comp_price[]
            curr_price.append({"price": companies[v]['price']})

        owned_value = list()
        # loops through total_shares[]
        for i in range(len(total_shares)):
            owned = dict()
            # appends each total value to owned{} after multiplying total_shares[] values with curr_price[] values
            owned["stock_total_value"] = total_shares[i][next(
                iter(total_shares[i]))] * curr_price[i][next(iter(curr_price[i]))]
            # for each value given to owned[] its passed to owned_value[]
            owned_value.append(owned)

        total = []
        # loops through owned value
        for key in range(len(owned_value)):
            # pulls total values for each stock
            total.append(owned_value[key]['stock_total_value'])
        # adds to cash
        net_worth = cash + sum(total)

        current_price = {}
        total_value = {}
        for data in range(len(index)):
            # pull price data from curr_price[] and assign to current_price{} at data's index value
            current_price["price"] = curr_price[data][next(
                iter(curr_price[data]))]
            # pull stock value data from total_value[] and assign to total_value{} at data's index value
            total_value["total_stock_value"] = owned_value[data][next(
                iter(owned_value[data]))]
            # update index with curremt_price{} at data's index value
            index[data].update({'price': usd(current_price["price"])})
            # update index with total_value{} value at data's index value
            index[data].update(
                {'total_stock_value': usd(total_value["total_stock_value"])})

        net_worth = usd(net_worth)

    else:
        net_worth = 'N/A'

    return render_template('index.html', user=username, index=index, cash=usd(cash), total=net_worth)


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """TODO: add a personal touch"""
    user_id = session['user_id']
    username = db.execute(
        'SELECT username FROM users WHERE id = :user_id', user_id=user_id)
    username = username[0]['username']

    # looks up the amount of funds the current user has
    cash = db.execute(
        'SELECT cash FROM users WHERE id = :user_id', user_id=user_id)
    cash = int(cash[0]['cash'])
    # redirects user to the buy page
    if request.method == 'GET':
        return render_template('account.html')

    elif request.method == 'POST':
        deposit = request.form.get('deposit')

        funds = cash + float(deposit)
        # updates user funds amount
        db.execute('UPDATE users SET cash = :cash WHERE id = :user_id',
                   cash=funds, user_id=user_id)

        # displays a message to the user confirming the purchase
        flash('Deposit Confirmed!')
        # Redirect user to home page
        return redirect("/")


@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    """TODO: add a personal touch"""
    user_id = session['user_id']
    username = db.execute(
        'SELECT username FROM users WHERE id = :user_id', user_id=user_id)
    username = username[0]['username']
    # redirects user to the buy page
    if request.method == 'GET':
        return render_template('delete.html')

    elif request.method == 'POST':
        db.execute('DELETE FROM users WHERE id = :user_id', user_id=user_id)
        db.execute(
            'DELETE FROM transactions WHERE user_id = :user_id', user_id=user_id)
        db.execute(
            'DELETE FROM owned_shares WHERE user_id = :user_id', user_id=user_id)
        # logs user out of deleted account
        return redirect("/logout")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """TODO: Buy shares of stock"""
    # date/ time variable for transaction dates/ times
    date = datetime.datetime.now()
    # gets inputted stock symbol from database
    symbol = request.form.get('symbol')
    if symbol != None:
        symbol = symbol.upper()
    # selects the profile of the current user
    user_id = session['user_id']

    # looks up the amount of funds the current user has
    cash = db.execute(
        'SELECT cash FROM users WHERE id = :user_id', user_id=user_id)
    cash = int(cash[0]['cash'])

    # redirects user to the buy page
    if request.method == 'GET':
        return render_template('buy.html')

    elif request.method == 'POST':
        company = lookup(symbol)

        # checks for form errors
        if symbol == '':
            return apology('Please enter a stock symbol')

        if company == None:
            return apology('Company not found')

        # converts the amount given from a string (all html inputs normally return strings, need a integer) to a integer
        amount = request.form.get('shares')

        try:
            amount = int(amount)
        except:
            return apology('Please enter a valid amount')

        if amount <= 0 or amount is None:
            return apology('Please enter a valid amount')

        # the amount being charged, based on the shares input multiplied by the stock price
        total = amount * company['price']

        if total > cash:
            return apology('Insufficient funds')

        else:

            transaction = 'BUY'
            # subtracts cash spent from total funds
            debit = cash - total
            # updates user funds amount
            db.execute('UPDATE users SET cash = :cash WHERE id = :user_id',
                       cash=debit, user_id=user_id)

            # initialises row
            db.execute('INSERT INTO transactions (user_id, user_transaction, company, symbol, shares, total_shares, price, transaction_type, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       user_id, 0, company['name'], symbol, amount, amount, company['price'], transaction, date)
            # checks user's previous transaction number
            transaction_number = db.execute(
                'SELECT user_transaction FROM transactions WHERE user_id = :user_id ORDER BY user_transaction DESC LIMIT 1', user_id=user_id)
            transaction_number = int(transaction_number[0]['user_transaction'])
            transaction_number += 1
            # updates transaction number
            db.execute('UPDATE transactions SET user_transaction = :transaction_number WHERE date = :date',
                       transaction_number=transaction_number, date=date)

            # updates shares to reflect purchase
            db.execute('UPDATE transactions SET shares = :shares WHERE user_id = :user_id AND symbol = :symbol AND user_transaction = :transaction_number',
                       shares=amount, user_id=user_id, symbol=symbol, transaction_number=transaction_number)

            sum_shares = db.execute(
                'SELECT SUM(shares) FROM transactions WHERE user_id = :user_id AND symbol = :symbol', user_id=user_id, symbol=symbol)
            sum_shares = int(sum_shares[0]['SUM(shares)'])
            # updates total shares to reflect sale
            db.execute('UPDATE transactions SET total_shares = :shares WHERE user_id = :user_id AND symbol = :symbol AND user_transaction = :transaction_number',
                       shares=sum_shares, user_id=user_id, symbol=symbol, transaction_number=transaction_number)

            # checks for existing stock of same symbol to input data for owned shares table
            owned_stock = db.execute(
                'SELECT symbol FROM owned_shares WHERE user_id = :user_id', user_id=user_id)
            owned = []
            for i in range(len(owned_stock)):
                owned.append(owned_stock[i]['symbol'])
            # if not first stock
            if owned[0] != 'N/A':
                # checks if company is already owned
                if symbol not in owned:
                    # if not owned, inserts new row into owned shares table
                    db.execute('INSERT INTO owned_shares (user_id, company, symbol, total_shares, date) VALUES (?, ?, ?, ?, ?)',
                               user_id, company['name'], symbol, sum_shares, date)
                else:
                    # if owned, updates total
                    db.execute('UPDATE owned_shares SET total_shares = :total_shares, date = :date WHERE user_id = :user_id AND symbol = :symbol',
                               total_shares=sum_shares, date=date, user_id=user_id, symbol=symbol)

            # if first stock purchase
            else:
                if owned[0] == 'N/A':
                    # updates placeholder to reflect symbol
                    db.execute(
                        'UPDATE owned_shares SET company = :company, symbol = :symbol WHERE user_id = :user_id', company=company['name'], symbol=symbol, user_id=user_id)
                    # updates total amount and date
                    db.execute('UPDATE owned_shares SET total_shares = :total_shares, date = :date WHERE user_id = :user_id AND symbol = :symbol',
                               total_shares=sum_shares, date=date, user_id=user_id, symbol=symbol)

            # displays a message to the user confirming the purchase
            flash('Purchase Confirmed!')
            # Redirect user to home page
            return redirect("/")


@app.route("/history")
@login_required
def history():
    """TODO: Show history of transactions"""
    # selects the profile of the current user
    user_id = session['user_id']
    username = db.execute(
        'SELECT username FROM users WHERE id = :user_id', user_id=user_id)
    username = username[0]['username']

    history = db.execute(
        'SELECT user_transaction, company, symbol, shares, total_shares, transaction_type, date FROM transactions WHERE user_id = :user_id', user_id=user_id)

    prices = db.execute(
        'SELECT price FROM transactions WHERE user_id = :user_id', user_id=user_id)

    price = {}
    for data in range(len(history)):

        price["price"] = prices[data][next(iter(prices[data]))]

        history[data].update({'price': usd(price["price"])})

    print(history)

    return render_template('history.html', user=username, history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """TODO: Get stock quote."""
    # redirects user to the quote page
    if request.method == 'GET':
        return render_template('quote.html')

    elif request.method == 'POST':

        symbol = request.form.get('symbol')
        company = lookup(symbol.upper())

        # checks for form errors
        if symbol == '':
            return apology('Please enter a stock symbol')

        elif company == None:
            return apology('Company not found')

        else:
            price = usd(company['price'])
        # if none are found, redirects to the results page and shows requested information
        return render_template('user-quote.html', name=company['name'], price=price, symbol=company['symbol'])


@app.route("/register", methods=["GET", "POST"])
def register():
    """TODO: Register user"""
    # accesses what the user has input by calling the names on each input field and assigning each to a variable
    username = request.form.get('username')
    password = request.form.get('password')
    confirm = request.form.get('confirmation')

    # redirects user to the register page
    if request.method == 'GET':
        return render_template('register.html')

    elif request.method == 'POST':
        # checks for mistakes, incomplete fields, used usernames and informs the user of any issues
        if username == '' or password == '' or confirm == '':
            return apology('Please complete all fields')

        if password != confirm:
            return apology('Passwords do not match')

        else:
            # creates a hash of the inputted password when no issues are detected
            hash = generate_password_hash(password)
            try:
                # inserts information into users table
                new_user = db.execute(
                    'INSERT INTO users (username, hash) VALUES (?, ?)', username, hash)

            except:
                return apology('Username is taken')

        time.sleep(0.01)
        session["user_id"] = new_user
        # initialize owned shares table row for new user
        user = session["user_id"]
        db.execute('INSERT INTO owned_shares (user_id, company, symbol, total_shares, date) VALUES (?, ?, ?, ?, ?)',
                   user, 'N/A', 'N/A', 0, 'N/A')

        return redirect('/')


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """TODO: Sell shares of stock"""

    # date/ time variable for transaction dates/ times
    date = datetime.datetime.now()

    # selects the profile of the current user
    user_id = session['user_id']

    # looks up the amount of funds the current user has
    cash = db.execute('SELECT cash FROM users WHERE id = :id', id=user_id)
    cash = int(cash[0]['cash'])

    curr_owned = db.execute(
        'SELECT symbol FROM owned_shares WHERE user_id = :user_id', user_id=user_id)
    # redirects user to the sell page
    if request.method == 'GET':
        return render_template('sell.html', symbols=[row["symbol"] for row in curr_owned])

    elif request.method == 'POST':
        # gets selected stock symbol from form
        symbol = request.form.get('symbol')
        print('symbol: ', symbol)
        company = lookup(symbol)
        # converts the amount given from a string (all html inputs normally return strings, need a integer) to a integer
        amount = request.form.get('shares')
        # checks for form errors

        try:
            amount = int(amount)
        except:
            return apology('Please enter a valid amount')

        if amount <= 0 or amount is None:
            return apology('Please enter a valid amount')

        shares = db.execute(
            'SELECT total_shares FROM owned_shares WHERE user_id = :user_id AND symbol = :symbol', user_id=user_id, symbol=symbol)
        print('shares: ', shares)
        total_shares = int(shares[0]['total_shares'])
        if total_shares < amount:
            return apology('Insufficient shares')

        else:
            # the amount being sold, based on the shares input multiplied by the stock price
            total = amount * company['price']
            # adds cash made to total funds
            profit = total + cash

            transaction = 'SELL'

            # updates user funds amount
            db.execute('UPDATE users SET cash = :cash WHERE id = :user_id',
                       cash=profit, user_id=user_id)

            # initialises row
            db.execute('INSERT INTO transactions (user_id, user_transaction, company, symbol, shares, price, transaction_type, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       user_id, 1, company['name'], symbol, amount, company['price'], transaction, date)
            # checks user's previous transaction number
            transaction_number = db.execute(
                'SELECT user_transaction FROM transactions WHERE user_id = :user_id ORDER BY user_transaction DESC LIMIT 1', user_id=user_id)
            transaction_number = int(transaction_number[0]['user_transaction'])
            transaction_number += 1
            # updates current transaction number
            db.execute('UPDATE transactions SET user_transaction = :transaction_number WHERE date = :date',
                       transaction_number=transaction_number, date=date)

            # updates shares to reflect sale
            db.execute('UPDATE transactions SET shares = :shares WHERE user_id = :user_id AND symbol = :symbol AND user_transaction = :transaction_number',
                       shares=-abs(amount), user_id=user_id, symbol=symbol, transaction_number=transaction_number)

            sum_shares = db.execute(
                'SELECT SUM(shares) FROM transactions WHERE user_id = :user_id AND symbol = :symbol', user_id=user_id, symbol=symbol)
            sum_shares = int(sum_shares[0]['SUM(shares)'])
            # updates total shares in transactions to reflect sale
            db.execute('UPDATE transactions SET total_shares = :shares WHERE user_id = :user_id AND symbol = :symbol AND user_transaction = :transaction_number',
                       shares=sum_shares, user_id=user_id, symbol=symbol, transaction_number=transaction_number)
            # updates total shares in owne shares to reflect sale
            db.execute('UPDATE owned_shares SET total_shares = :total_shares, date = :date WHERE user_id = :user_id AND symbol = :symbol',
                       total_shares=sum_shares, date=date, user_id=user_id, symbol=symbol)
            # displays a message to the user confirming the sale
            flash('Sale Confirmed!')
            # Redirect user to home page
            return redirect("/")
