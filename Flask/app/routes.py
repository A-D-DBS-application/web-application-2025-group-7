from flask import render_template, request, redirect, url_for
from .models import Kot

def register_routes(app):
    @app.route('/')
    def index():
        koten = Kot.query.all()
        return render_template('index.html', koten=koten)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # Implement simple login, just as a placeholder
        if request.method == 'POST':
            naam = request.form['naam']
            # Store naam in session or use as needed
            return redirect(url_for('index'))
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        # Implement simple registration, just as a placeholder
        if request.method == 'POST':
            naam = request.form['naam']
            email = request.form['email']
            telefoon = request.form['telefoon']
            universiteit = request.form['universiteit']
            # Here, you would add this new student to the database.
            return redirect(url_for('login'))
        return render_template('register.html')
