from operator import and_
from warnings import filters
from flask import render_template, request, redirect, url_for, session, flash, send_file
import io
from werkzeug.utils import secure_filename
import os, time
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func
from .models import Beschikbaarheid, db, Gebruiker, Student, Huurder, Kot, Boeking, Kotbaas
from datetime import datetime, timedelta
# import weasyprint
from app.services.prijs_algoritme import bereken_aangeraden_prijs
from app.models import Kot  # indien nog niet toegevoegd



DEFAULT_TOURIST_TAX_RATE = 0.06  # 6% standaardtoeslag op de totale omzet

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

        query = Kot.query.filter_by(goedgekeurd=True) # Alleen goedgekeurde koten tonen

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
            rol = request.form['rol']
            # Admin login only when 'admin' role is selected
            if rol == 'admin':
                admin_username = request.form.get('admin_username', '').strip()
                admin_password = request.form.get('admin_password', '').strip()
                if admin_username == 'GitooAdmin' and admin_password == 'Gitoo123':
                    session['rol'] = 'admin'
                    return redirect(url_for('dashboard_admin'))
                else:
                    flash('Ongeldige admin inloggegevens.')
                    return render_template('login.html')

            naam = request.form['naam'].strip()
            email = request.form.get('email', '').strip()  # optioneel veld

            gebruiker = None
            if email:
                gebruiker = Gebruiker.query.filter_by(email=email).first()
            if not gebruiker and naam:
                gebruiker = Gebruiker.query.filter_by(naam=naam).first()

            if gebruiker:
                if email.endswith('@gitoo.be'):
                    session['gebruiker_id'] = gebruiker.gebruiker_id
                    session['rol'] = 'admin'
                    return redirect(url_for('index'))
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
    gebruiker = Gebruiker.query.get(session['gebruiker_id'])

    if not gebruiker:
        flash('Gebruiker niet gevonden.', 'error')
        return redirect(url_for('login'))

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

        # Kotbaas info
        beschrijving = None
        foto_url = ''
        if rol in ['kotbaas', 'admin']:
            beschrijving = request.form.get('beschrijving', '').strip() or None
            foto_url = request.form.get('foto', '').strip() or ''

        # Datums
        startdatum_str = request.form['startdatum']
        einddatum_str = request.form['einddatum']

        startdatum = datetime.strptime(startdatum_str, "%Y-%m-%d")
        einddatum = datetime.strptime(einddatum_str, "%Y-%m-%d")

        if einddatum <= startdatum:
            flash("Einddatum moet later zijn dan startdatum.", "error")
            return redirect(url_for('add_kot'))

        # Naam van tegenpartij
        student_id = None
        kotbaas_id = None

        if rol == 'student':
            kotbaas_voornaam = request.form.get('kotbaas_voornaam', '').strip()
            kotbaas_achternaam = request.form.get('kotbaas_achternaam', '').strip()

            if not kotbaas_voornaam or not kotbaas_achternaam:
                flash('Vul zowel voornaam als achternaam van de kotbaas in.', 'error')
                return render_template('add_kot.html', rol=rol, gebruiker=gebruiker)

            kotbaas_naam = f"{kotbaas_voornaam} {kotbaas_achternaam}"
            kotbaas = Gebruiker.query.filter_by(naam=kotbaas_naam, type='kotbaas').first()

            if not kotbaas:
                flash('Naam fout getypt of kotbaas niet geregistreerd.', 'error')
                return render_template('add_kot.html', rol=rol, gebruiker=gebruiker)

            kotbaas_id = kotbaas.gebruiker_id
            student_id = session['gebruiker_id']

        elif rol == 'kotbaas':
            eigenaar_voornaam = request.form.get('eigenaar_voornaam', '').strip()
            eigenaar_achternaam = request.form.get('eigenaar_achternaam', '').strip()
            gebruiker.naam = f"{eigenaar_voornaam} {eigenaar_achternaam}"

            student_naam = request.form['student_naam'].strip()
            student = Gebruiker.query.filter_by(naam=student_naam, type='student').first()

            if not student:
                flash('Naam fout getypt of student niet geregistreerd.', 'error')
                return render_template('add_kot.html', rol=rol, gebruiker=gebruiker)

            kotbaas_id = gebruiker.gebruiker_id
            student_id = student.gebruiker_id

        # Initiatiefnemer-logica
        initiatiefnemer_checked = bool(request.form.get('initiatiefnemer'))
        initiatiefnemer = 'student' if (rol == 'student' and initiatiefnemer_checked) else 'kotbaas'
        if rol == 'kotbaas' and not initiatiefnemer_checked:
            initiatiefnemer = 'student'

        #PRIJSALGORITME: AANGERADEN PRIJS BEREKENEN  
        aangeraden_prijs = bereken_aangeraden_prijs(
            stad=stad,
            oppervlakte=oppervlakte,
            aantal_slaapplaatsen=aantal_slaapplaatsen
        )

        flash(f"Op basis van gelijkaardige koten raden we een maandhuurprijs van €{aangeraden_prijs:.2f} aan.", "info")

        # Kot opslaan
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
            beschrijving=beschrijving,
            foto=foto_url,
            initiatiefnemer=initiatiefnemer,
        )
        db.session.add(kot)
        db.session.commit()

        # Beschikbaarheid opslaan
        beschikbaarheid = Beschikbaarheid(
            kot_id=kot.kot_id,
            startdatum=startdatum,
            einddatum=einddatum,
            status_beschikbaarheid="beschikbaar"
        )
        db.session.add(beschikbaarheid)
        db.session.commit()

        flash("Kot succesvol toegevoegd!", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_kot.html', rol=session.get('rol'), gebruiker=gebruiker)

    
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
        if 'gebruiker_id' not in session or session.get('rol') != 'huurder':
            flash('Log eerst in als huurder om een kot te boeken.', 'error')
            return redirect(url_for('login'))

        kot = Kot.query.get_or_404(kot_id)
        huurder = Huurder.query.get(session['gebruiker_id'])
        if not huurder:
            flash('Je hebt een huurderprofiel nodig om te boeken.', 'error')
            return redirect(url_for('dashboard'))

        default_start = datetime.now().date()
        default_end = default_start + timedelta(days=30)

        if request.method == 'POST':
            startdatum_str = request.form.get('startdatum', '').strip()
            einddatum_str = request.form.get('einddatum', '').strip()
            aantal_personen_str = request.form.get('aantal_personen', '1').strip()
            voorkeuren_str = request.form.get('voorkeuren', '').strip()

            fouten = False
            startdatum = None
            einddatum = None

            try:
                startdatum = datetime.strptime(startdatum_str, "%Y-%m-%d")
                einddatum = datetime.strptime(einddatum_str, "%Y-%m-%d")
                if einddatum <= startdatum:
                    flash('Einddatum moet later zijn dan startdatum.', 'error')
                    fouten = True
            except ValueError:
                flash('Ongeldige start- of einddatum.', 'error')
                fouten = True

            try:
                aantal_personen = int(aantal_personen_str)
                if aantal_personen <= 0:
                    raise ValueError
            except ValueError:
                flash('Aantal personen moet een positief geheel getal zijn.', 'error')
                fouten = True
                aantal_personen = None

            max_personen = kot.aantal_slaapplaatsen or 0
            if not fouten and max_personen and aantal_personen > max_personen:
                flash(f'Er is maximaal plaats voor {max_personen} personen in dit kot.', 'error')
                fouten = True

            if fouten:
                return render_template(
                    'boek.html',
                    kot=kot,
                    default_start=startdatum_str or default_start.strftime('%Y-%m-%d'),
                    default_end=einddatum_str or default_end.strftime('%Y-%m-%d'),
                    form_data=request.form,
                    huurder=huurder
                )

            dagen = max((einddatum - startdatum).days, 1)
            maandprijs = float(kot.maandhuurprijs or 0)
            egwkosten = float(kot.egwkosten or 0)
            totale_maandprijs = maandprijs + egwkosten
            dagprijs = totale_maandprijs / 30 if totale_maandprijs else 0
            totaalprijs = dagprijs * dagen

            # Voorkeuren opslaan bij huurder
            if voorkeuren_str:
                huurder.voorkeuren = voorkeuren_str
                db.session.commit()

            boeking = Boeking(
                gebruiker_id=huurder.gebruiker_id,
                kot_id=kot.kot_id,
                startdatum=startdatum,
                einddatum=einddatum,
                totaalprijs=totaalprijs,
                status_boeking='in afwachting',
                aantal_personen=aantal_personen
            )
            db.session.add(boeking)
            db.session.commit()
            flash('Boeking aangevraagd! We houden je op de hoogte.', 'success')
            return redirect(url_for('dashboard'))

        return render_template(
            'boek.html',
            kot=kot,
            default_start=default_start.strftime('%Y-%m-%d'),
            default_end=default_end.strftime('%Y-%m-%d'),
            form_data=None,
            huurder=huurder
        )

    # Admin-only: update beschrijving
    @app.route('/admin/kot/<int:kot_id>/update_description', methods=['POST'])
    def admin_update_description(kot_id):
        if session.get('rol') != 'admin':
            return redirect(url_for('login'))
        kot = Kot.query.get_or_404(kot_id)
        nieuwe_beschrijving = request.form.get('beschrijving', '').strip()
        kot.beschrijving = nieuwe_beschrijving or None
        db.session.commit()
        flash('Beschrijving bijgewerkt.', 'success')
        # Redirect terug naar juiste beheer pagina indien daarvandaan gekomen
        if request.referrer and 'dashboard_admin_koten' in request.referrer:
            return redirect(url_for('dashboard_admin_koten'))
        return redirect(url_for('index'))

    # Admin-only: update foto URL
    @app.route('/admin/kot/<int:kot_id>/update_photo', methods=['POST'])
    def admin_update_photo(kot_id):
        if session.get('rol') != 'admin':
            return redirect(url_for('login'))
        kot = Kot.query.get_or_404(kot_id)
        # 1) If a file is uploaded, save it under static/uploads and set foto to its URL
        file = request.files.get('foto_file')
        if file and file.filename:
            filename = secure_filename(file.filename)
            # allow only common image extensions
            allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            ext = os.path.splitext(filename)[1].lower()
            if ext in allowed:
                uploads_dir = os.path.join(app.static_folder, 'uploads')
                os.makedirs(uploads_dir, exist_ok=True)
                unique_name = f"kot{kot_id}_{int(time.time())}{ext}"
                save_path = os.path.join(uploads_dir, unique_name)
                file.save(save_path)
                # store absolute static path so templates don't need changes
                static_rel = f"uploads/{unique_name}"
                kot.foto = url_for('static', filename=static_rel)
            else:
                flash('Bestandstype niet toegestaan. Gebruik jpg, jpeg, png, gif of webp.', 'error')
        else:
            # 2) Fallback to URL field if provided
            nieuwe_foto = request.form.get('foto', '').strip()
            if nieuwe_foto:
                kot.foto = nieuwe_foto
        db.session.commit()
        flash('Foto-URL bijgewerkt.', 'success')
        if request.referrer and 'dashboard_admin_koten' in request.referrer:
            return redirect(url_for('dashboard_admin_koten'))
        return redirect(url_for('index'))

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
        pending_koten = Kot.query.filter_by(kotbaas_id=kotbaas.gebruiker_id, goedgekeurd=False).all()
        return render_template(
            'dashboard_kotbaas.html',
            naam=kotbaas.gebruiker.naam,
            koten=koten,
            pending_koten=pending_koten
        )
    
    @app.route('/dashboard_admin')
    def dashboard_admin():
        if 'rol' not in session or session['rol'] != 'admin':
            return redirect(url_for('login'))
        zoekterm = request.args.get('zoekterm', '').strip()

        boeking_query = Boeking.query \
            .outerjoin(Huurder, Boeking.gebruiker_id == Huurder.gebruiker_id) \
            .outerjoin(Gebruiker, Huurder.gebruiker_id == Gebruiker.gebruiker_id) \
            .outerjoin(Kot, Boeking.kot_id == Kot.kot_id)

        if zoekterm:
            patroon = f"%{zoekterm.lower()}%"
            boeking_query = boeking_query.filter(
                or_(
                    func.lower(Gebruiker.naam).like(patroon),
                    func.lower(Gebruiker.email).like(patroon),
                    func.lower(func.coalesce(Gebruiker.telefoon, '')).like(patroon),
                    func.lower(Kot.adres).like(patroon),
                    func.lower(Kot.stad).like(patroon),
                    func.lower(Boeking.status_boeking).like(patroon)
                )
            )

        boekingen = boeking_query.all()
        return render_template('admin_booking_overview.html', boekingen=boekingen, zoekterm=zoekterm)

    @app.route('/dashboard_admin_koten')
    def dashboard_admin_koten():
        if 'rol' not in session or session['rol'] != 'admin':
            return redirect(url_for('login'))
        zoekterm = request.args.get('zoekterm', '').strip()
        kot_query = Kot.query.options(
            joinedload(Kot.kotbaas).joinedload(Kotbaas.gebruiker),
            joinedload(Kot.student).joinedload(Student.gebruiker),
            joinedload(Kot.boekingen)
        )

        if zoekterm:
            patroon = zoekterm.lower()

            def kot_match(kot):
                velden = [
                    kot.adres or '',
                    kot.stad or '',
                    kot.beschrijving or '',
                ]
                if kot.kotbaas and kot.kotbaas.gebruiker:
                    velden.append(kot.kotbaas.gebruiker.naam or '')
                    velden.append(kot.kotbaas.gebruiker.email or '')
                if kot.student and kot.student.gebruiker:
                    velden.append(kot.student.gebruiker.naam or '')
                    velden.append(kot.student.gebruiker.email or '')
                return any(patroon in veld.lower() for veld in velden)

            alle_koten = kot_query.all()
            koten = [k for k in alle_koten if kot_match(k)]
        else:
            koten = kot_query.all()
        kot_statistieken = {}

        for kot in koten:
            maandhuur = float(kot.maandhuurprijs or 0)
            egwkosten = float(kot.egwkosten or 0)
            totale_maandlast = maandhuur + egwkosten
            omzet_per_nacht = totale_maandlast / 30 if totale_maandlast else 0
            totale_omzet = 0.0

            for boeking in kot.boekingen:
                totaalprijs = float(boeking.totaalprijs or 0)
                totale_omzet += totaalprijs

            toeristenbelasting = totale_omzet * DEFAULT_TOURIST_TAX_RATE
            egw_aandeel_omzet = totale_omzet * (egwkosten / totale_maandlast) if totale_maandlast else 0
            egw_per_nacht = egwkosten / 30 if egwkosten else 0

            kot_statistieken[kot.kot_id] = {
                'omzet_per_nacht': omzet_per_nacht,
                'totale_omzet': totale_omzet,
                'toeristenbelasting': toeristenbelasting,
                'omzet_na_belasting': max(totale_omzet - toeristenbelasting, 0.0),
                'egw_per_maand': egwkosten,
                'egw_per_nacht': egw_per_nacht,
                'egw_aandeel_omzet': egw_aandeel_omzet,
            }

        return render_template(
            'admin_kot_list.html',
            koten=koten,
            kot_statistieken=kot_statistieken,
            tourist_tax_rate=DEFAULT_TOURIST_TAX_RATE,
            zoekterm=zoekterm
        )

    @app.route('/admin/kot/<int:kot_id>/edit', methods=['GET', 'POST'])
    def admin_kot_edit(kot_id):
        if session.get('rol') != 'admin':
            return redirect(url_for('login'))
        kot = Kot.query.get_or_404(kot_id)
        if request.method == 'POST':
            nieuwe_beschrijving = request.form.get('beschrijving', '').strip()
            kot.beschrijving = nieuwe_beschrijving or None
            # Foto via URL
            foto_url = request.form.get('foto', '').strip()
            # Foto via upload
            file = request.files.get('foto_file')
            if file and file.filename:
                filename = secure_filename(file.filename)
                allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
                ext = os.path.splitext(filename)[1].lower()
                if ext in allowed:
                    uploads_dir = os.path.join(app.static_folder, 'uploads')
                    os.makedirs(uploads_dir, exist_ok=True)
                    unique_name = f"kot{kot_id}_{int(time.time())}{ext}"
                    save_path = os.path.join(uploads_dir, unique_name)
                    file.save(save_path)
                    static_rel = f"uploads/{unique_name}"
                    kot.foto = url_for('static', filename=static_rel)
                else:
                    flash('Bestandstype niet toegestaan.', 'error')
            elif foto_url:
                kot.foto = foto_url
            db.session.commit()
            flash('Kot bijgewerkt.', 'success')
            return redirect(url_for('dashboard_admin_koten'))
        return render_template('admin_edit_kot.html', kot=kot)

    @app.route('/admin/kot/<int:kot_id>/delete', methods=['POST'])
    def admin_delete_kot(kot_id):
        if session.get('rol') != 'admin':
            flash('Geen toegang tot deze actie.', 'error')
            return redirect(url_for('login'))
        kot = Kot.query.get_or_404(kot_id)
        for boeking in list(kot.boekingen):
            db.session.delete(boeking)
        for beschikbaarheid in list(kot.beschikbaarheden):
            db.session.delete(beschikbaarheid)
        db.session.delete(kot)
        db.session.commit()
        flash('Kot en gekoppelde boekingen verwijderd.', 'success')
        return redirect(url_for('dashboard_admin_koten'))

    @app.route('/admin/boeking/<int:boeking_id>/delete', methods=['POST'])
    def admin_delete_boeking(boeking_id):
        if session.get('rol') != 'admin':
            flash('Geen toegang tot deze actie.', 'error')
            return redirect(url_for('login'))
        boeking = Boeking.query.get_or_404(boeking_id)
        if boeking.status_boeking and 'geannuleerd' in boeking.status_boeking.lower():
            flash('Deze boeking was al geannuleerd.', 'info')
            return redirect(url_for('dashboard_admin'))
        boeking.status_boeking = 'geannuleerd'
        db.session.commit()
        flash('Boeking gemarkeerd als geannuleerd.', 'success')
        return redirect(url_for('dashboard_admin'))

    @app.route('/boeking/<int:boeking_id>/cancel', methods=['POST'])
    def cancel_boeking(boeking_id):
        if 'gebruiker_id' not in session:
            return redirect(url_for('login'))
        gebruiker = Gebruiker.query.get(session['gebruiker_id'])
        if not gebruiker or not gebruiker.huurder:
            flash('Deze actie is alleen voor huurders.', 'error')
            return redirect(url_for('dashboard'))
        boeking = Boeking.query.get_or_404(boeking_id)
        if boeking.gebruiker_id != gebruiker.huurder.gebruiker_id:
            flash('Je kan enkel je eigen boekingen annuleren.', 'error')
            return redirect(url_for('dashboard'))
        if boeking.status_boeking and 'geannuleerd' in boeking.status_boeking.lower():
            flash('Deze boeking was al geannuleerd.', 'info')
            return redirect(url_for('dashboard'))
        boeking.status_boeking = 'geannuleerd'
        db.session.commit()
        flash('Boeking succesvol geannuleerd.', 'success')
        return redirect(url_for('dashboard'))
    
    @app.route('/approve_kot/<int:kot_id>', methods=['POST']) # Kotbaas moet kot eerst goedkeuren
    def approve_kot(kot_id):
        kot = Kot.query.get_or_404(kot_id)
        if 'gebruiker_id' not in session or session.get('rol') != 'kotbaas' or session['gebruiker_id'] != kot.kotbaas_id:
            flash("Je mag alleen je eigen koten goedkeuren.", "error")
            return redirect(url_for('dashboard_kotbaas'))
        kot.goedgekeurd = True
        db.session.commit()
        flash("Kot succesvol goedgekeurd en zichtbaar gemaakt.", "success")
        return redirect(url_for('dashboard_kotbaas'))
    
    @app.route('/generate_contract/<int:kot_id>')
    def generate_contract(kot_id):
        kot = Kot.query.get_or_404(kot_id)
        contract_html = render_template('contract_template.html',
            kotbaas_naam=kot.kotbaas.gebruiker.naam,
            kotbaas_email=kot.kotbaas.gebruiker.email,
            kotbaas_telefoon=kot.kotbaas.gebruiker.telefoon,
            student_naam=kot.student.gebruiker.naam,
            student_email=kot.student.gebruiker.email,
            student_telefoon=kot.student.gebruiker.telefoon,
            kot_adres=kot.adres,
            kot_oppervlakte=kot.oppervlakte
        )
        pdf = weasyprint.HTML(string=contract_html).write_pdf()
        return send_file(
            io.BytesIO(pdf),
            as_attachment=True,
            download_name=f"Gitoo_Contract_{kot_id}.pdf",
            mimetype='application/pdf'
        )


    
