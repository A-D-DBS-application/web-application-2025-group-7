from operator import and_
from warnings import filters
from flask import render_template, request, redirect, url_for, session, flash
from .models import Beschikbaarheid, db, Gebruiker, Student, Huurder, Kot, Boeking, Kotbaas
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
            'startdatum': request.args.get('startdatum', '').strip(),
            'einddatum': request.args.get('einddatum', '').strip(),
        }

        query = Kot.query

        if filters['stad']:
            query = query.filter(Kot.stad.ilike(f"%{filters['stad']}%"))
        if filters['max_huur']:
            try:
                waarde = float(filters['max_huur'])
                if waarde >= 0:
                    query = query.filter(Kot.maandhuurprijs <= waarde)
            except ValueError:
                pass
        if filters['min_oppervlakte']:
            try:
                waarde = int(filters['min_oppervlakte'])
                if waarde >= 0:
                    query = query.filter(Kot.oppervlakte >= waarde)
            except ValueError:
                pass
        if filters['aantal_slaapplaatsen']:
            try:
                waarde = int(filters['aantal_slaapplaatsen'])
                if waarde >= 0:
                    query = query.filter(Kot.aantal_slaapplaatsen >= waarde)
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
                waarde = float(filters['max_egwkosten'])
                if waarde >= 0:
                    query = query.filter(Kot.egwkosten <= waarde)
            except ValueError:
                pass

        from sqlalchemy import and_
        if filters['startdatum'] and filters['einddatum']:
            try:
                start = datetime.strptime(filters['startdatum'], "%Y-%m-%d")
                end = datetime.strptime(filters['einddatum'], "%Y-%m-%d")
                query = query.join(Beschikbaarheid).filter(
                    and_(
                        Beschikbaarheid.startdatum <= start,
                        Beschikbaarheid.einddatum >= end
                    )
                )
            except ValueError:
                pass

        from sqlalchemy.orm import joinedload
        koten = query.options(joinedload(Kot.beschikbaarheden)).all()
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
                elif rol == 'kotbaas' and not getattr(bestaande_gebruiker, 'kotbaas', None):
                    kotbaas = Kotbaas(gebruiker_id=bestaande_gebruiker.gebruiker_id)
                    db.session.add(kotbaas)
                    db.session.commit()
                session['gebruiker_id'] = bestaande_gebruiker.gebruiker_id
                if email.endswith('@gitoo.be'):
                    session['rol'] = 'admin'
                    return redirect(url_for('dashboard_admin'))
                session['rol'] = rol
                if rol == 'kotbaas':
                    return redirect(url_for('dashboard_kotbaas'))
                else:
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
                elif rol == 'kotbaas':
                    kotbaas = Kotbaas(gebruiker_id=gebruiker.gebruiker_id)
                    db.session.add(kotbaas)
                db.session.commit()
                session['gebruiker_id'] = gebruiker.gebruiker_id
                if email.endswith('@gitoo.be'):
                    session['rol'] = 'admin'
                    return redirect(url_for('dashboard_admin'))
                session['rol'] = rol
                if rol == 'kotbaas':
                    return redirect(url_for('dashboard_kotbaas'))
                else:
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
                if email.endswith('@gitoo.be'):
                    session['gebruiker_id'] = gebruiker.gebruiker_id
                    session['rol'] = 'admin'
                    return redirect(url_for('dashboard_admin'))
                elif rol == 'student' and gebruiker.student:
                    session['gebruiker_id'] = gebruiker.gebruiker_id
                    session['rol'] = 'student'
                    return redirect(url_for('dashboard'))
                elif rol == 'huurder' and gebruiker.huurder:
                    session['gebruiker_id'] = gebruiker.gebruiker_id
                    session['rol'] = 'huurder'
                    return redirect(url_for('dashboard'))
                elif rol == 'kotbaas' and getattr(gebruiker, 'kotbaas', None):
                    session['gebruiker_id'] = gebruiker.gebruiker_id
                    session['rol'] = 'kotbaas'
                    return redirect(url_for('dashboard_kotbaas'))
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
        if getattr(gebruiker, 'kotbaas', None):
            rollen.append('kotbaas')

        if request.method == 'POST':
            gekozen_rol = request.form.get('switch_rol')
            if gekozen_rol in rollen:
                session['rol'] = gekozen_rol
                actieve_rol = gekozen_rol

        if actieve_rol == 'kotbaas' and getattr(gebruiker, 'kotbaas', None):
            return redirect(url_for('dashboard_kotbaas'))

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
        if 'gebruiker_id' not in session or session.get('rol') not in ['student', 'kotbaas']:
            return redirect(url_for('login'))
        rol = session.get('rol')

        if request.method == 'POST':
            # Kotgegevens ophalen
            adres = request.form['adres']
            stad = request.form['stad']
            oppervlakte = int(request.form['oppervlakte'])
            aantal_slaapplaatsen = int(request.form['aantal_slaapplaatsen'])
            maandhuurprijs = float(request.form['maandhuurprijs'])
            egwkosten = float(request.form.get('egwkosten', 0))
            eigen_keuken = bool(request.form.get('eigen_keuken'))
            eigen_sanitair = bool(request.form.get('eigen_sanitair'))

            startdatum_str = request.form['startdatum']
            einddatum_str = request.form['einddatum']

            startdatum = datetime.strptime(startdatum_str, "%Y-%m-%d")
            einddatum = datetime.strptime(einddatum_str, "%Y-%m-%d")

            if einddatum <= startdatum:
                flash("Einddatum moet later zijn dan startdatum.", "error")
                return redirect(url_for('add_kot'))

            # Naam van tegenpartij opvragen en valideren
            student_id = None
            kotbaas_id = None

            if rol == 'student':
                kotbaas_naam = request.form['kotbaas_naam'].strip()
                kotbaas = Gebruiker.query.filter_by(naam=kotbaas_naam, type='kotbaas').first()
                if not kotbaas:
                    flash('Naam is fout getypt of kotbaas is nog niet geregistreerd op onze website.', 'error')
                    return render_template('add_kot.html', rol=rol)
                kotbaas_id = kotbaas.gebruiker_id
                student_id = session['gebruiker_id']
            elif rol == 'kotbaas':
                student_naam = request.form['student_naam'].strip()
                student = Gebruiker.query.filter_by(naam=student_naam, type='student').first()
                if not student:
                    flash('Naam is fout getypt of student is nog niet geregistreerd op onze website.', 'error')
                    return render_template('add_kot.html', rol=rol)
                kotbaas_id = session['gebruiker_id']
                student_id = student.gebruiker_id

            # Initiatiefnemer-logica
            initiatiefnemer_checked = bool(request.form.get('initiatiefnemer'))
            if rol == 'student':
                initiatiefnemer = 'student' if initiatiefnemer_checked else 'kotbaas'
            else:
                initiatiefnemer = 'kotbaas' if initiatiefnemer_checked else 'student'

            # Kot aanmaken
            kot = Kot(
                student_id=student_id,
                kotbaas_id=kotbaas_id,
                adres=adres,
                stad=stad,
                oppervlakte=oppervlakte,
                aantal_slaapplaatsen=aantal_slaapplaatsen,
                maandhuurprijs=maandhuurprijs,
                eigen_keuken=eigen_keuken,
                eigen_sanitair=eigen_sanitair,
                egwkosten=egwkosten,
                goedgekeurd=False,
                foto='',
                initiatiefnemer=initiatiefnemer
            )
            db.session.add(kot)
            db.session.commit()

            # Beschikbaarheid koppelen aan kot
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

        # GET: juiste formulier tonen met goede rol
        return render_template('add_kot.html', rol=session.get('rol'))
    
    @app.route('/verwijder_kot/<int:kot_id>', methods=['POST'])
    def verwijder_kot(kot_id):
        if 'gebruiker_id' not in session or session.get('rol') not in ['student', 'kotbaas']:
            return redirect(url_for('login'))

        kot = Kot.query.get_or_404(kot_id)
        gebruiker_id = session['gebruiker_id']
        rol = session['rol']

        # Enkel eigenaar student/kotbaas mag verwijderen
        if rol == 'student' and kot.student_id == gebruiker_id:
            pass
        elif rol == 'kotbaas' and kot.kotbaas_id == gebruiker_id:
            pass
        else:
            flash('Je hebt geen rechten om dit kot te verwijderen.', 'error')
            return redirect(url_for('dashboard'))

        # Verwijder eerst bijbehorende beschikbaarheden en boekingen
        Beschikbaarheid.query.filter_by(kot_id=kot_id).delete()
        Boeking.query.filter_by(kot_id=kot_id).delete()

        db.session.delete(kot)
        db.session.commit()
        flash('Kot succesvol verwijderd!')
        if rol == 'student':
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('dashboard_kotbaas'))


    @app.route('/boek/<int:kot_id>', methods=['GET', 'POST'])
    def boek(kot_id):
        kot = Kot.query.get_or_404(kot_id)
        if request.method == 'POST':
            # Boekingslogica komt hier indien gewenst
            pass
        return render_template('boek.html', kot=kot)

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index'))


    @app.route('/dashboard_kotbaas')
    def dashboard_kotbaas():
        if 'gebruiker_id' not in session or session.get('rol') != 'kotbaas':
            return redirect(url_for('login'))

        kotbaas = Kotbaas.query.get(session['gebruiker_id'])
        # Geeft alle koten waarbij hij kotbaas is
        koten = Kot.query.filter_by(kotbaas_id=kotbaas.gebruiker_id).all()
        return render_template(
            'dashboard_kotbaas.html',
            naam=kotbaas.gebruiker.naam,
            koten=koten
        )

    @app.route('/dashboard_admin')
    def dashboard_admin():
        if 'rol' not in session or session['rol'] != 'admin':
            return redirect(url_for('login'))
        boekingen = Boeking.query.all()
        return render_template('dashboard_admin.html', boekingen=boekingen)

