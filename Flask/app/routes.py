from flask import render_template, request, redirect, url_for, session, flash
from .models import Beschikbaarheid, db, Gebruiker, Student, Huurder, Kot, Boeking
from datetime import datetime

def register_routes(app):

    @app.route('/', methods=['GET'])
    def index():
        # Filters ophalen uit de querystring (GET-parameters)
        filters = {
            'stad': request.args.get('stad', '').strip(),
            'max_huur': request.args.get('max_huur', '').strip(),
            'min_oppervlakte': request.args.get('min_oppervlakte', '').strip(),
            'aantal_slaapplaatsen': request.args.get('aantal_slaapplaatsen', '').strip(),
            'brandveiligheidsconformiteit': request.args.get('brandveiligheidsconformiteit'),
            'eigen_keuken': request.args.get('eigen_keuken'),
            'eigen_sanitair': request.args.get('eigen_sanitair'),
            'max_egwkosten': request.args.get('max_egwkosten', '').strip(),
        }

        query = Kot.query

        if filters['stad']:
            query = query.filter(Kot.stad.ilike(f"%{filters['stad']}%"))
        if filters['max_huur']:
            try:
                query = query.filter(Kot.maandhuurprijs <= float(filters['max_huur']))
            except ValueError:
                pass
        if filters['min_oppervlakte']:
            try:
                query = query.filter(Kot.oppervlakte >= int(filters['min_oppervlakte']))
            except ValueError:
                pass
        if filters['aantal_slaapplaatsen']:
            try:
                query = query.filter(Kot.aantal_slaapplaatsen >= int(filters['aantal_slaapplaatsen']))
            except ValueError:
                pass
        if filters['brandveiligheidsconformiteit'] == '1':
            query = query.filter(Kot.brandveiligheidsconformiteit.is_(True))
        if filters['eigen_keuken'] == '1':
            query = query.filter(Kot.eigen_keuken.is_(True))
        if filters['eigen_sanitair'] == '1':
            query = query.filter(Kot.eigen_sanitair.is_(True))
        if filters['max_egwkosten']:
            try:
                query = query.filter(Kot.egwkosten <= float(filters['max_egwkosten']))
            except ValueError:
                pass

        koten = query.all()
        return render_template('index.html', koten=koten, filters=filters)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            naam = request.form['naam']
            email = request.form['email']
            telefoon = request.form['telefoon']
            rol = request.form['rol']
            universiteit = request.form.get('universiteit') if rol == 'student' else None

            bestaande_gebruiker = Gebruiker.query.filter_by(email=email).first()
            if bestaande_gebruiker:
                # Voeg toe wat nog nodig is qua rol
                if rol == 'student' and not bestaande_gebruiker.student:
                    bestaande_gebruiker.student = Student(gebruiker_id=bestaande_gebruiker.gebruiker_id, universiteit=universiteit)
                    db.session.commit()
                elif rol == 'huurder' and not bestaande_gebruiker.huurder:
                    bestaande_gebruiker.huurder = Huurder(gebruiker_id=bestaande_gebruiker.gebruiker_id)
                    db.session.commit()
                session['gebruiker_id'] = bestaande_gebruiker.gebruiker_id
                session['rol'] = rol
                return redirect(url_for('dashboard'))
            else:
                gebruiker = Gebruiker(
                    naam=naam,
                    email=email,
                    telefoon=telefoon,
                    type=rol,
                    aangemaakt_op=datetime.now()
                )
                db.session.add(gebruiker)
                db.session.commit()
                if rol == 'student':
                    student = Student(
                        gebruiker_id=gebruiker.gebruiker_id,
                        universiteit=universiteit
                    )
                    db.session.add(student)
                elif rol == 'huurder':
                    huurder = Huurder(gebruiker_id=gebruiker.gebruiker_id)
                    db.session.add(huurder)
                db.session.commit()
                session['gebruiker_id'] = gebruiker.gebruiker_id
                session['rol'] = rol
                return redirect(url_for('dashboard'))
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            naam = request.form['naam'].strip()
            email = request.form.get('email', '').strip()  # optioneel veld
            rol = request.form['rol']

            gebruiker = None
            if email:
                gebruiker = Gebruiker.query.filter_by(email=email).first()
            if not gebruiker and naam:
                gebruiker = Gebruiker.query.filter_by(naam=naam).first()

            if gebruiker:
                if rol == 'student' and gebruiker.student:
                    session['gebruiker_id'] = gebruiker.gebruiker_id
                    session['rol'] = 'student'
                    return redirect(url_for('dashboard'))
                elif rol == 'huurder' and gebruiker.huurder:
                    session['gebruiker_id'] = gebruiker.gebruiker_id
                    session['rol'] = 'huurder'
                    return redirect(url_for('dashboard'))
                else:
                    flash('Deze gebruiker heeft deze rol niet. Kies een andere rol of registreer je voor deze.')
            else:
                flash('Gebruiker niet gevonden! Controleer naam/email.')
        return render_template('login.html')

    @app.route('/dashboard', methods=['GET', 'POST'])
    def dashboard():
        if 'gebruiker_id' not in session:
            return redirect(url_for('login'))
        gebruiker_id = session['gebruiker_id']
        actieve_rol = session.get('rol', 'student')
        gebruiker = Gebruiker.query.get(gebruiker_id)
        rollen = []
        if gebruiker.student:
            rollen.append('student')
        if gebruiker.huurder:
            rollen.append('huurder')

        # Rol wisselen via dropdown/selectie in dashboard
        if request.method == 'POST':
            gekozen_rol = request.form.get('switch_rol')
            if gekozen_rol in rollen:
                session['rol'] = gekozen_rol
                actieve_rol = gekozen_rol

        if actieve_rol == 'student' and gebruiker.student:
            koten = Kot.query.filter_by(student_id=gebruiker.student.gebruiker_id).all()
            inbox = Boeking.query.join(Kot).filter(Kot.student_id == gebruiker.student.gebruiker_id).all()
            return render_template(
                'dashboard_student.html',
                koten=koten,
                inbox=inbox,
                naam=gebruiker.naam,
                rollen=rollen,
                actieve_rol=actieve_rol
            )
        elif actieve_rol == 'huurder' and gebruiker.huurder:
            boekingen = Boeking.query.filter_by(gebruiker_id=gebruiker.huurder.gebruiker_id).all()
            return render_template(
                'dashboard_huurder.html',
                boekingen=boekingen,
                naam=gebruiker.naam,
                rollen=rollen,
                actieve_rol=actieve_rol
            )
        else:
            # fallback
            return redirect(url_for('index'))

    @app.route('/add_kot', methods=['GET', 'POST'])
    def add_kot():
        if 'gebruiker_id' not in session or session.get('rol') != 'student':
            return redirect(url_for('login'))
        student = Student.query.filter_by(gebruiker_id=session['gebruiker_id']).first()
        if not student:
            flash("Alleen studenten kunnen koten toevoegen.")
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            #kotgegevens ophalen
            adres = request.form['adres']
            stad = request.form['stad']
            oppervlakte = int(request.form['oppervlakte'])
            aantal_slaapplaatsen = int(request.form['aantal_slaapplaatsen'])
            maandhuurprijs = float(request.form['maandhuurprijs'])
            egwkosten = float(request.form.get('egwkosten', 0))
            eigen_keuken = bool(request.form.get('eigen_keuken'))
            eigen_sanitair = bool(request.form.get('eigen_sanitair'))

            #start en einddatum
            startdatum_str = request.form['startdatum']
            einddatum_str = request.form['einddatum']

            startdatum = datetime.strptime(startdatum_str, "%Y-%m-%d")
            einddatum = datetime.strptime(einddatum_str, "%Y-%m-%d")

            if einddatum <= startdatum:
                flash("Einddatum moet later zijn dan startdatum")
                return redirect(url_for('add_kot'))
        
            #nieuw kot aanmaken 
            kot = Kot(
                student_id=session['gebruiker_id'],
                adres=request.form['adres'],
                stad=request.form['stad'],
                oppervlakte=int(request.form['oppervlakte']),
                aantal_slaapplaatsen=int(request.form['aantal_slaapplaatsen']),
                maandhuurprijs=float(request.form['maandhuurprijs']),
                eigen_keuken=bool(request.form.get('eigen_keuken')),
                eigen_sanitair=bool(request.form.get('eigen_sanitair')),
                egwkosten=float(request.form['egwkosten']),
                goedgekeurd=False,
                foto=''
            )
            db.session.add(kot)
            db.session.commit()
            #beschikbaarheid koppelen aan kot
            beschikbaarheid = Beschikbaarheid(
                kot_id=kot.kot_id,
                startdatum=startdatum,
                einddatum=einddatum,
                status_beschikbaarheid="beschikbaar"
            )
            db.session.add(beschikbaarheid)
            db.session.commit()

            flash("Kot succesvol toegevoegd met beschikbaarheidsperiode!")
            return redirect(url_for('dashboard'))
        return render_template('add_kot.html')

    @app.route('/boek/<int:kot_id>', methods=['GET', 'POST'])
    def boek(kot_id):
        if 'gebruiker_id' not in session or session.get('rol') != 'huurder':
            return redirect(url_for('login'))
        kot = Kot.query.get_or_404(kot_id)
        if request.method == 'POST':
            boeking = Boeking(
                gebruiker_id=session['gebruiker_id'],
                kot_id=kot_id,
                startdatum=datetime.now(),
                einddatum=datetime.now(),
                totaalprijs=kot.maandhuurprijs,
                status_boeking="in afwachting"
            )
            db.session.add(boeking)
            db.session.commit()
            return redirect(url_for('dashboard'))
        return render_template('boek.html', kot=kot)

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))

