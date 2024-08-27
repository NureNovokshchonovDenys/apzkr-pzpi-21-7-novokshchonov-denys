from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Конфігурація MongoDB
app.config['MONGO_URI'] = 'mongodb+srv://admin:admin@coursework.ww1zt.mongodb.net/course?retryWrites=true&w=majority&appName=coursework'
mongo = PyMongo(app)
db = mongo.db

# Головна сторінка
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Реєстрація користувача
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        # Перевірка, чи користувач вже існує
        user = mongo.db.users.find_one({'username': username})

        if user:
            flash('Користувач з таким ім\'ям вже існує!')
            return redirect(url_for('register'))

        # Додавання нового користувача в базу даних
        mongo.db.users.insert_one({
            'username': username,
            'password': hashed_password
        })

        flash('Реєстрація пройшла успішно! Тепер можна увійти.')
        return redirect(url_for('login'))

    return render_template('register.html')

# Вхід користувача
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Перевірка наявності користувача і коректності пароля
        user = mongo.db.users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Невірне ім\'я користувача або пароль!')

    return render_template('login.html')

# Панель користувача
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Отримання кімнат, створених користувачем
    rooms = mongo.db.rooms.find({'username': session['username']})
    return render_template('dashboard.html', rooms=rooms)

# Створення нової кімнати
@app.route('/create_room', methods=['POST'])
def create_room():
    if 'username' not in session:
        return redirect(url_for('login'))

    room_name = request.form['room_name']
    sensors = request.form.getlist('sensors')

    # Додавання нової кімнати в базу даних
    mongo.db.rooms.insert_one({
        'username': session['username'],
        'name': room_name,
        'sensors': sensors
    })

    return redirect(url_for('dashboard'))

# Сторінка кімнати
@app.route('/room/<room_id>')
def room(room_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    # Отримання даних кімнати і відповідних датчиків
    room = mongo.db.rooms.find_one({'_id': ObjectId(room_id)})
    sensors_data = [mongo.db.sensors.find_one({'COM': sensor}) for sensor in room['sensors']]

    return render_template('room.html', room=room, sensors=sensors_data)

# Обробка даних з датчика
@app.route('/sensor_data', methods=['POST'])
def sensor_data():
    data = request.json
    com_port = data['COM']

    # Оновлення даних датчика або додавання нового запису
    mongo.db.sensors.update_one(
        {'COM': com_port},
        {'$set': {
            'h': data['h'],
            't': data['t'],
            'p': data['p'],
            'pol': data['pol'],
            'dewp': data['dewp'],
            'timestamp': datetime.datetime.utcnow()
        }},
        upsert=True
    )

    return 'Дані оновлено!', 200

# Адмін панель

# Відображення сторінки адміністратора
@app.route('/admin')
def admin_panel():
    users = list(db.users.find())
    rooms = list(db.rooms.find())
    return render_template('admin.html', users=users, rooms=rooms)

# Редагування користувача
@app.route('/admin/edit_user/<user_id>', methods=['POST'])
def edit_user(user_id):
    username = request.form['username']
    db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'username': username}})
    return redirect(url_for('admin_panel'))

# Видалення користувача
@app.route('/admin/delete_user/<user_id>', methods=['POST'])
def delete_user(user_id):
    db.users.delete_one({'_id': ObjectId(user_id)})
    return redirect(url_for('admin_panel'))

# Редагування кімнати
@app.route('/admin/edit_room/<room_id>', methods=['POST'])
def edit_room(room_id):
    name = request.form['name']
    db.rooms.update_one({'_id': ObjectId(room_id)}, {'$set': {'name': name}})
    return redirect(url_for('admin_panel'))

# Видалення кімнати
@app.route('/admin/delete_room/<room_id>', methods=['POST'])
def delete_room(room_id):
    db.rooms.delete_one({'_id': ObjectId(room_id)})
    return redirect(url_for('admin_panel'))

# Експорт бази даних у форматі JSON
@app.route('/admin/export', methods=['GET'])
def export_db():
    data = {
        'users': list(db.users.find({}, {'_id': 0})),
        'rooms': list(db.rooms.find({}, {'_id': 0})),
        'sensors': list(db.sensors.find({}, {'_id': 0}))
    }
    return jsonify(data)

# Вихід з акаунту
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
