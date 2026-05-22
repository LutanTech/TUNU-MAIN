from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import hashlib, hmac, json, secrets, string, os
import re
app = Flask(__name__)
from dotenv import load_dotenv

load_dotenv()

app.config['SECRET_KEY'] = 'THIS_IS_SO_SECRET_FOR_2026_TUNU'
DATABASE_URL = os.getenv("DB_URL")
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60 * 60 * 24 * 30
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'info.tunupublishers@gmail.com'
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('Tunu Publishers','info.tunupublishers@gmail.com')
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'books')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
from flask import abort

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {
        "sslmode": "disable"
    }
}

db = SQLAlchemy(app)
mail = Mail(app)
migrate = Migrate(app, db)

def generate_id(prefix='STF', length=6):
    chars = string.ascii_uppercase + string.digits
    return prefix + '-' + ''.join(secrets.choice(chars) for _ in range(length))

def generate_hmac_token(data):
    payload = json.dumps(data, sort_keys=True)
    return hmac.new(app.config['SECRET_KEY'].encode(), payload.encode(), hashlib.sha256).hexdigest()

def verify_hmac_token(data, token):
    return hmac.compare_digest(generate_hmac_token(data), token)

def log_action(action, status_code=200, staff_id=None):
    try:
        log = Log(
            staff_id=staff_id,
            action=action,
            method=request.method,
            endpoint=request.path,
            ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            status_code=status_code
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print("Manual log failed:", e)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('staff_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = Staff.query.filter_by(id=session.get('staff_id')).first()
        if not user:
            return redirect(url_for('login'))
        if not user.is_admin and not user.is_super_admin:
            abort(401, description='You do not have enough permissions to view this page')
        return f(*args, **kwargs)
    return wrapper

class Staff(db.Model):
    id = db.Column(db.String(20), primary_key=True, default=lambda: generate_id('STF'))
    name = db.Column(db.String(512), nullable=False)
    email = db.Column(db.String(128), unique=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    location = db.Column(db.String(128), default='Nairobi')
    password = db.Column(db.String(), nullable=False)
    added_at = db.Column(db.DateTime, default=lambda: datetime.utcnow()+timedelta(hours=3))
    edited_at = db.Column(db.DateTime, default=lambda: datetime.utcnow()+timedelta(hours=3))
    edited_by = db.Column(db.String(), db.ForeignKey('staff.id'))
    deactivated_by = db.Column(db.String(), db.ForeignKey('staff.id'))
    deactivated_at = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_super_admin = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id':self.id,
            'name':self.name,
            'phone':self.phone,
            'email':self.email,
            'location':self.location,
            'is_active':self.is_active,
            'is_admin':self.is_admin
            }

class Book(db.Model):
    id = db.Column(db.String(20), primary_key=True, default=lambda: generate_id('BK'))
    title = db.Column(db.String(512), nullable=False)
    image = db.Column(db.String(), default='https://i.ibb.co/CKRYPD4p/image.png')
    grade = db.Column(db.String(100))
    slug = db.Column(db.String(100))
    audience = db.Column(db.String(100))
    authors = db.Column(db.Text)
    added_by = db.Column(db.String(20), db.ForeignKey('staff.id'))
    oldPrice = db.Column(db.Float, default=0)
    newPrice = db.Column(db.Float, default=0)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_by = db.Column(db.String(20), db.ForeignKey('staff.id') )
    views = db.Column(db.Integer, default=0)
    sold = db.Column(db.Integer, default=0)
    
    
    def set_slug(self):
        self.slug = re.sub(r'[^a-z0-9]+', '_', self.title.lower())[:100].strip('_')   
             
    def to_dict(self):
        return {'id':self.id,'title':self.title,'image':self.image,'grade':self.grade,'audience':self.audience,'authors':self.authors,'oldPrice':self.oldPrice,'newPrice':self.newPrice, "slug": self.slug}

class Submission(db.Model):
    id = db.Column(db.String(20), primary_key=True, default=lambda: generate_id('SUB', 4))

    staff_id = db.Column(db.String(20), db.ForeignKey('staff.id'), nullable=False)

    staffName = db.Column(db.String(128), nullable=False)

    institution_name = db.Column(db.String(256), nullable=False)

    contact_person = db.Column(db.String(128), nullable=True)

    phone = db.Column(db.String(20), nullable=True)

    category = db.Column(db.String(100), nullable=True)

    conversation_notes = db.Column(db.Text, nullable=True)

    challenges = db.Column(db.Text, nullable=True)

    submitted_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=3))

    def to_dict(self):
        return {
            'id': self.id,
            'staffName': self.staffName,
            'institution_name': self.institution_name,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'category': self.category,
            'conversation_notes': self.conversation_notes,
            'challenges': self.challenges,
            'time': self.submitted_at.strftime('%H:%M'),
            'date': self.submitted_at.strftime('%Y-%m-%d')
        }


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    staff_id = db.Column(db.String(20), db.ForeignKey('staff.id'), nullable=True)
    action = db.Column(db.String(256), nullable=False)

    method = db.Column(db.String(10))
    endpoint = db.Column(db.String(256))
    ip = db.Column(db.String(50))
    user_agent = db.Column(db.String(512))

    status_code = db.Column(db.Integer)

    timestamp = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=3))

    def to_dict(self):
        staff = Staff.query.filter_by(id=self.staff_id).first()
        return {
            'id': self.id,
            'staff': staff.name if staff else 'Anonymous',
            'action': self.action,
            'method': self.method,
            'endpoint': self.endpoint,
            'ip': self.ip,
            'user_agent': self.user_agent,
            'status': self.status_code,
            'time': self.timestamp
        }

BOOKS_DATA = [
    {'title':'Fundo la Moyoni','newPrice':500,'oldPrice':550,'url':'/static/books/fundo.jpeg','audience':'General','grade':'Adult','authors':'Tunu'},
    {'title':'Fragments of Survival','newPrice':650,'oldPrice':0,'url':'/static/books/fragments.jpeg','audience':'General','grade':'Adult','authors':'Tunu'},
    {'title':'CBC English Grade 6','newPrice':700,'oldPrice':850,'url':'/static/books/dawa_ya_moyoni.jpeg','audience':'Students','grade':'Grade 6','authors':'Tunu'}
]

@app.route('/')
def home():
    rating = Book.query.filter_by(is_deleted=False)\
        .order_by(Book.views.desc())\
        .limit(6)\
        .all()

    best_selling = Book.query.filter_by(is_deleted=False)\
        .order_by(Book.sold.desc())\
        .limit(6)\
        .all()

    return render_template(
        'index.html',
        books_data={
            'rating': [b.to_dict() for b in rating],
            'best_selling': [b.to_dict() for b in best_selling]
        }
    )
    
@app.route('/base')
def base():
    return render_template('base.html')

@app.after_request
def cache_static_books(response):
    if request.path.startswith('/static/books/'):
        response.cache_control.max_age = 60 * 60 * 24 * 30
        response.cache_control.public = True
    return response

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/base2')
def base2():
    return render_template('books.html')

@app.route('/books')
def books():
    books = Book.query.filter_by(is_deleted=False).all()
    return render_template('books.html', books_data=[b.to_dict() for b in books])

@app.route('/staff/login', methods=['GET','POST'])
def login():
    if request.method=='GET':
        return render_template('login.html')
    
    
    user = Staff.query.filter_by(phone=request.form.get('phone')).first()
    if not user:
       user = Staff.query.filter_by(id=request.form.get('phone')).first()
       
    if not user:
        return render_template('login.html', error='Account not found. Please contact Admin'), 500
    
    if not user or not check_password_hash(user.password, request.form.get('password')):
        log_action(f'Invalid login by {user.name}', 401, user.id)
        return render_template('login.html', error='invalid credentials')
    
    session['staff_id']=user.id
    
    if not user.is_super_admin:      
        log_action(f'{user.name } logged in', 200, user.id)
    
    return redirect(url_for('dashboard'))

@app.route('/staff/logout')
@login_required
def logout():
    staff = Staff.query.filter_by(id=session.get('staff_id')).first()
    
    if not staff.is_super_admin:      
        log_action(f'{staff.name } logged in', 200, staff.id)   
         
    session.clear()
    return redirect(url_for('home'))

@app.route('/staff/dashboard')
@login_required
def dashboard():

    staff = Staff.query.filter_by(id=session.get('staff_id')).first()

    books = Book.query.filter_by(is_deleted=False).all()

    visits_this_month = Submission.query.filter(
        Submission.submitted_at >= datetime.utcnow() - timedelta(days=30)
    ).count()

    reports_today = Submission.query.filter(
        Submission.staffName == staff.name,
        Submission.submitted_at >= datetime.utcnow().date()
    ).count()

    recent_submissions = Submission.query.order_by(
        Submission.submitted_at.desc()
    ).limit(4).all()
    
    if not staff.is_super_admin:      
        log_action(f'{staff.name } logged in', 200, staff.id)
        
    return render_template(
        'dashboard.html',
        staff=staff,
        books=books,
        visits_this_month=visits_this_month,
        reports_today=reports_today,
        recent_submissions=recent_submissions,
        start_time=datetime.utcnow()
    )


@app.route('/staff/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    data = request.form

    if Staff.query.filter_by(phone=data.get('phone')).first():
        return render_template('register.html', error='phone already exists')

    if data.get('email') and Staff.query.filter_by(email=data.get('email')).first():
        return render_template('register.html', error='email already exists')

    user = Staff(
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone'),
        password=generate_password_hash(data.get('password'))
    )

    db.session.add(user)
    db.session.commit()

    return redirect(url_for('login'))

@app.route('/submit-report', methods=['POST'])
@login_required
def submit_report():

    staff = Staff.query.filter_by(id=session.get('staff_id')).first()

    data = request.form

    if not data.get('institution_name'):
        return jsonify({'error': 'institution required'}), 400

    submission = Submission(
        staff_id=staff.id,
        staffName=staff.name,
        institution_name=data.get('institution_name'),
        contact_person=data.get('contact_person'),
        phone=data.get('phone'),
        category=data.get('category'),
        conversation_notes=data.get('conversation_notes'),
        challenges=data.get('challenges')
    )

    db.session.add(submission)
    db.session.commit()

    return redirect(url_for('dashboard'))

@app.route('/create_dummy')
def create_dummy():
    with app.app_context():
        db.create_all()
    admin = Staff.query.filter_by(phone='0700000000').first()
    if not admin:
        admin = Staff(name='Admin',phone='0700000000',password=generate_password_hash('admin123'),is_admin=True)
        db.session.add(admin);db.session.commit()
    created=[]
    for i in BOOKS_DATA:
        if Book.query.filter_by(title=i['title']).first(): continue
        b=Book(title=i['title'],image=i['url'],grade=i['grade'],audience=i['audience'],authors=i['authors'],added_by=admin.id,newPrice=i['newPrice'],oldPrice=i['oldPrice'])
        b.set_slug()
        db.session.add(b)
        created.append(i['title'])
    db.session.commit()
    return jsonify({'created':created})

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    admin = Staff.query.filter_by(id=session.get('staff_id')).first()


    allStaff = Staff.query.filter_by(is_super_admin=False).all()

    books = Book.query.filter_by(is_deleted=False).all()

    visits_this_month = Submission.query.filter(
        Submission.submitted_at >= datetime.utcnow() - timedelta(days=30)
    ).count()

    reports_today = Submission.query.filter(
        Submission.submitted_at >= datetime.utcnow().date()
    ).count()

    recent_submissions = Submission.query.order_by(
        Submission.submitted_at.desc()
    ).limit(4).all()

    if admin and not admin.is_super_admin:
        log_action(
            f'Admin {admin.name} accessed their dashboard',
            200,
            admin.id
        )
        
    
    staff_dict= [s.to_dict() for s in allStaff]
    
    # return jsonify({
    #     'staff': [s.to_dict() for s in allStaff]
    # }), 200

    return render_template(
        'admin.html',
        admin=admin,
        books=books,
        staff_dict=staff_dict,
        visits_this_month=visits_this_month,
        reports_today=reports_today,
        recent_submissions=recent_submissions,
        start_time=datetime.utcnow()
    )
    
    
@app.route('/api/admin/edit/staff', methods=['POST']) 
@login_required
@admin_required
def edit_staff():
    data = request.get_json()
    id = data.get('id')
    
    admin = Staff.query.filter_by(id=session.get('staff_id')).first()
    
    staff = Staff.query.filter_by(id=id).first()
    if not staff:
        return jsonify({'error':'Staff not found'}), 404
    if staff.is_super_admin:
        return jsonify({'error':'Unauthorized'}), 401
    if staff.is_admin:
        return jsonify({'msg':'An alert sent to the Director for confirmation'}), 200
    
    if not admin.is_super_admin:      
        log_action(f'Admin {admin.name } is editing staff by ID {staff.id}', 200, admin.id)
        
    try:
        staff.name = data.get('name')
        staff.email = data.get('email')
        staff.phone = data.get('phone')
        staff.location = data.get('location')
        staff.is_admin = data.get('is_admin')
        staff.edited_at = datetime.utcnow() + timedelta(hours=3)
        staff.edited_by = session.get('staff_id')
        db.session.commit()
        return jsonify({'msg':'Edited successfully'}), 200
    except Exception as e:
        db.session.rollback()
        log_action(f'Admin {admin.name } encountered {str(e)} when editing staff by name {staff.name}', 200, admin.id)
        return jsonify({'error':f'Failed to edit staff. ERROR: [{str(e)}]'}), 500

@app.route('/api/admin/toggle/staff', methods=['POST'])
@login_required
@admin_required
def toggle_staff():
    data = request.get_json()
    id = data.get('staff_id')
    if not id:
        return jsonify({'error':'Missing data in request'}), 404
    
    admin = Staff.query.filter_by(id=session.get('staff_id')).first()
    
    staff = Staff.query.filter_by(id=id).first()
    if not staff:
        return jsonify({'error':'Staff not found in Database'}), 404
    if staff.is_super_admin:
        return redirect(url_for(unauthorized(error='You do not have enough permissions to view this page')))
    staff.is_active = not staff.is_active
    staff.deactivated_by = session.get('staff_id')
    staff.deactivated_at = datetime.utcnow() + timedelta(hours=3)
    db.session.commit()
    
    if not admin.is_super_admin:      
        log_action(f'Admin {admin.name } togled staff status for {staff.name}', 200, admin.id)
    return jsonify({'msg':'Staff toggled successfully'}), 200
from werkzeug.utils import secure_filename

@app.route('/api/admin/add_book', methods=['POST'])
@login_required
@admin_required
def add_book():
    # Capture text fields from standard multi-part form
    title = request.form.get("title")
    authors = request.form.get("authors")
    grade = request.form.get("grade", "")
    audience = request.form.get("audience", "")
    
    # Handle the numeric details with safe defaults
    try:
        new_price = float(request.form.get("newPrice", 0))
        old_price = float(request.form.get("oldPrice", 0)) if request.form.get("oldPrice") else 0
    except ValueError:
        return jsonify({'error': 'Invalid format provided for prices.'}), 400

    # Business classification logic for audience/grade matching your system
    if len(grade) > 2 and not audience:
        audience = grade
        grade = ''

    # Handle the structural file upload stream
    image_file = request.files.get('image')
    image_url = "https://i.ibb.co/CKRYPD4p/image.png"  # Default if no file is uploaded

    if image_file and image_file.filename != '':
        # Sanitize filename string to eliminate relative path directory injection attacks
        filename = secure_filename(image_file.filename)
        
        # Append an epoch or unique string prefix if you want to avoid file overwriting
        unique_filename = f"{int(datetime.utcnow().timestamp())}_{filename}"
        
        # Determine target system path
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            # Commit binary payload stream directly to the local host operating system storage
            image_file.save(file_path)
            # Relative path matching your /static/ blueprint configuration routing setup
            image_url = f"/static/books/{unique_filename}"
        except Exception as e:
            return jsonify({'error': f'Failed writing image file payload to disk storage: {str(e)}'}), 500

    admin = Staff.query.filter_by(id=session.get('staff_id')).first()
    
    try:
        book = Book(
            title=title,
            image=image_url,
            oldPrice=old_price,
            newPrice=new_price,
            grade=grade,
            authors=authors,
            added_by=session.get('staff_id'),
            audience=audience
        )
        book.set_slug()
        db.session.add(book)
        db.session.commit()

        if not admin.is_super_admin:      
           log_action(f'Admin {admin.name} added a book titled {book.title} with local file asset storage.', 200, admin.id)

        return jsonify({"msg": "Book uploaded and saved successfully to host system storage!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database operation error occurred: {str(e)}'}), 500
    
@app.route('/api/admin/edit_book', methods=['POST'])
@login_required
@admin_required
def edit_book():

    raw = request.get_json()
    data = raw.get('data')

    admin = Staff.query.filter_by(id=session.get('staff_id')).first()


    book = Book.query.filter_by(id=data.get('id')).first()

    if not book:
        return jsonify({'error': 'Book to be edited not found'}), 404

    try:
        book.title = data.get("title")
        book.added_by = session.get('staff_id')
        book.oldPrice = data.get("oldPrice") or 0
        book.newPrice = data.get("newPrice")
        book.grade = data.get("grade")
        book.authors = data.get("authors")
        book.audience = data.get('audience')
        book.image = data.get('image')

        db.session.commit()

        return jsonify({'msg': 'Edited successfully'}), 200

    except Exception as e:
        db.session.rollback()
        log_action(f'Admin {admin.name } encountered {str(e)} when editing a book by title {book.title}', 200, admin.id)
        return jsonify({'error': f'Failed to edit {str(e)}'}), 500
    
@app.route('/api/admin/delete_book', methods=['POST'])
@login_required
@admin_required
def delete_book():
    data = request.get_json()
    id = data.get('id')
    
    admin = Staff.query.filter_by(id=session.get('staff_id')).first()
    
    book = Book.query.filter_by(id=id).first()
    if not book:
        return jsonify({'error':'Book to be deleted not found'}), 404
    try:
        book.is_deleted = True
        book.deleted_at = datetime.utcnow() + timedelta(hours=3)
        book.deleted_by = session.get('staff_id')
        db.session.commit()
        return jsonify({'msg':'Book deleted successfully'}),200
    except Exception as e:
        db.session.rollback()
        log_action(f'Admin {admin.name } encountered {str(e)} when deleting a book by title {book.title}', 200, admin.id)
        return jsonify({'error':f'Database error: {str(e)}'}), 500


@app.errorhandler(404)
def not_found(error):

    return render_template(
        '404.html', error=error
    ), 404

@app.errorhandler(500)
def backend_error(error):
    print(error)

    return render_template(
        '500.html',error=error
    ), 404

@app.errorhandler(401)
def unauthorized(error):
    return render_template(
        '401.html',
        error=error.description
    ), 401

@app.route('/create_db', methods=['GET'])
def create_db():
    with app.app_context():
        try:
            db.create_all()
            return jsonify({'msg':'Created tables succesfully'}), 200
        except Exception as e:
            return jsonify({'error':f'An error occured: {str(e)}'}), 500

if __name__=='__main__':
    with app.app_context():
       db.create_all()
    app.run(debug=True)