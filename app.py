from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------ MODELS ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    status = db.Column(db.String(20), default='active')  # Added status
    role = db.Column(db.String(20), default='bidder')    # Added role (seller/bidder)
    bids = db.relationship('Bid', backref='user', lazy=True)

# New Model for Auction Items
class AuctionItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    description = db.Column(db.Text)
    base_price = db.Column(db.Float)
    image_url = db.Column(db.String(300))
    status = db.Column(db.String(20), default='active')  # active, sold, removed
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.id'))
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)

class Auction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref='auctions')
    bids = db.relationship('Bid', backref='auction', lazy=True)

class Bid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey('auction.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float)
    bid_time = db.Column(db.DateTime, default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)
    rejected = db.Column(db.Boolean, default=False)

# ------------------ ROUTES ------------------

@app.before_first_request
def create_tables():
    db.create_all()
    if not User.query.filter_by(email="admin@example.com").first():
        admin = User(name="Admin", email="admin@example.com",
                     password=generate_password_hash("admin123"))
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def home():
    if 'admin' not in session:
        return redirect('/login')
    return redirect('/dashboard')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        admin = User.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password, password):
            session['admin'] = admin.id
            return redirect('/dashboard')
        else:
            flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/login')
    users = User.query.count()
    active_users = User.query.filter_by(status='active').count()
    inactive_users = User.query.filter_by(status='inactive').count()
    items = AuctionItem.query.count()
    active_items = AuctionItem.query.filter_by(status='active').count()
    auctions = Auction.query.count()
    bids = Bid.query.count()
    categories = Category.query.count()
    return render_template(
        'dashboard.html',
        users=users,
        active_users=active_users,
        inactive_users=inactive_users,
        items=items,
        active_items=active_items,
        auctions=auctions,
        bids=bids,
        categories=categories
    )

# ------------------ USERS ------------------


@app.route('/users')
def manage_users():
    if 'admin' not in session:
        return redirect('/login')
    users = User.query.all()
    return render_template('users.html', users=users)

# Add User
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'admin' not in session:
        return redirect('/login')
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        user = User(name=name, email=email, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        return redirect('/users')
    return render_template('user_form.html')

# Edit User
@app.route('/edit_user/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    if 'admin' not in session:
        return redirect('/login')
    user = User.query.get(id)
    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        user.status = request.form['status']
        user.role = request.form['role']
        db.session.commit()
        return redirect('/users')
    return render_template('user_form.html', user=user)

# Deactivate User
@app.route('/deactivate_user/<int:id>')
def deactivate_user(id):
    if 'admin' not in session:
        return redirect('/login')
    user = User.query.get(id)
    user.status = 'inactive'
    db.session.commit()
    return redirect('/users')

# Delete User (permanent)


@app.route('/reject_bid/<int:id>')
def reject_bid(id):
    if 'admin' not in session:
        return redirect('/login')
    bid = Bid.query.get(id)
    if bid:
        bid.rejected = True
        bid.approved = False
        db.session.commit()
        flash(f"Bid #{id} rejected!", "danger")
    else:
        # Dummy bid: just flash for demo
        flash(f"Dummy Bid #{id} rejected! (demo)", "danger")
    return redirect('/bids')

@app.route('/delete_bid/<int:id>')
def delete_bid(id):
    if 'admin' not in session:
        return redirect('/login')
    bid = Bid.query.get(id)
    if bid:
        db.session.delete(bid)
        db.session.commit()
        flash(f"Bid #{id} deleted!", "warning")
    else:
        # Dummy bid: just flash for demo
        flash(f"Dummy Bid #{id} deleted! (demo)", "warning")
    return redirect('/bids')

# ------------------ AUCTIONS ------------------

@app.route('/auctions')
def manage_auctions():
    if 'admin' not in session:
        return redirect('/login')
    auctions = Auction.query.all()
    return render_template('auctions.html', auctions=auctions)

# Update Auction Status
@app.route('/update_auction_status/<int:id>', methods=['POST'])
def update_auction_status(id):
    if 'admin' not in session:
        return redirect('/login')
    auction = Auction.query.get(id)
    auction.status = request.form['status']
    db.session.commit()
    return redirect('/auctions')

@app.route('/create_auction', methods=['GET', 'POST'])
def create_auction():
    if 'admin' not in session:
        return redirect('/login')
    categories = Category.query.all()
    if request.method == 'POST':
        new_auction = Auction(
            title=request.form['title'],
            description=request.form['description'],
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d'),
            category_id=request.form['category_id']
        )
        db.session.add(new_auction)
        db.session.commit()
        return redirect('/auctions')
    return render_template('auction_form.html', categories=categories)

@app.route('/edit_auction/<int:id>', methods=['GET', 'POST'])
def edit_auction(id):
    if 'admin' not in session:
        return redirect('/login')
    auction = Auction.query.get(id)
    categories = Category.query.all()
    if request.method == 'POST':
        auction.title = request.form['title']
        auction.description = request.form['description']
        auction.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        auction.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        auction.category_id = request.form['category_id']
        db.session.commit()
        return redirect('/auctions')
    return render_template('auction_form.html', auction=auction, categories=categories)

@app.route('/delete_auction/<int:id>')
def delete_auction(id):
    if 'admin' not in session:
        return redirect('/login')
    auction = Auction.query.get(id)
    db.session.delete(auction)
    db.session.commit()
    return redirect('/auctions')

# ------------------ BIDS ------------------

@app.route('/bids')
def manage_bids():
    if 'admin' not in session:
        return redirect('/login')
    bids = Bid.query.all()
    # If no real bids, show 10 dummy bids
    if not bids:
        from collections import namedtuple
        DummyBid = namedtuple('DummyBid', ['id', 'auction', 'user', 'amount', 'bid_time', 'approved', 'rejected'])
        class DummyObj:
            def __init__(self, name):
                self.name = name
        bids = [
            DummyBid(
                id=i+1,
                auction=DummyObj(f"Auction {i+1}"),
                user=DummyObj(f"User {i+1}"),
                amount=1000 + i*100,
                bid_time=f"2025-09-30 12:{str(i).zfill(2)}:00",
                approved=False,
                rejected=False
            ) for i in range(10)
        ]
    return render_template('bids.html', bids=bids)

# Delete Bid

# Approve Bid (optional, add 'approved' field in Bid model if needed)

# Approve Bid (optional, add 'approved' field in Bid model if needed)
@app.route('/approve_bid/<int:id>')
def approve_bid(id):
    if 'admin' not in session:
        return redirect('/login')
    bid = Bid.query.get(id)
    if bid:
        bid.approved = True
        bid.rejected = False
        db.session.commit()
    return redirect('/bids')

# @app.route('/reject_bid/<int:id>')
# def reject_bid(id):
#     if 'admin' not in session:
#         return redirect('/login')
#     bid = Bid.query.get(id)
#     if bid:
#         bid.rejected = True
#         bid.approved = False
#         db.session.commit()
#     return redirect('/bids')

# ------------------ MAIN ------------------

if __name__ == '__main__':
    app.run(debug=True)

# ------------------ AUCTION ITEMS ------------------

@app.route('/items')
def manage_items():
    if 'admin' not in session:
        return redirect('/login')
    items = AuctionItem.query.all()
    return render_template('items.html', items=items)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'admin' not in session:
        return redirect('/login')
    auctions = Auction.query.all()
    if request.method == 'POST':
        item = AuctionItem(
            name=request.form['name'],
            description=request.form['description'],
            base_price=request.form['base_price'],
            image_url=request.form['image_url'],
            auction_id=request.form['auction_id'],
            status=request.form['status']
        )
        db.session.add(item)
        db.session.commit()
        return redirect('/items')
    return render_template('item_form.html', auctions=auctions)

@app.route('/edit_item/<int:id>', methods=['GET', 'POST'])
def edit_item(id):
    if 'admin' not in session:
        return redirect('/login')
    item = AuctionItem.query.get(id)
    auctions = Auction.query.all()
    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        item.base_price = request.form['base_price']
        item.image_url = request.form['image_url']
        item.auction_id = request.form['auction_id']
        item.status = request.form['status']
        db.session.commit()
        return redirect('/items')
    return render_template('item_form.html', item=item, auctions=auctions)

@app.route('/delete_item/<int:id>')
def delete_item(id):
    if 'admin' not in session:
        return redirect('/login')
    item = AuctionItem.query.get(id)
    db.session.delete(item)
    db.session.commit()
    return redirect('/items')

# ------------------ NAVIGATION LINKS ------------------
# Add navigation links in your base.html for: Dashboard | Users | Items | Auctions | Bids | Categories | Logout
