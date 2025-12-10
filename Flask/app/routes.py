from operator import and_
from warnings import filters
from flask import render_template, request, redirect, url_for, session, flash, send_file
from .prijs_algoritme import bereken_aangeraden_prijs
from werkzeug.utils import secure_filename
import os, time
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func
from .models import (
    Beschikbaarheid,
    db,
    Gebruiker,
    Student,
    Huurder,
    Kot,
    Boeking,
    Kotbaas,
    Contract,
    SysteemInstelling,
)
from datetime import datetime, timedelta
# Bestandsupload instellingen voor contracten
UPLOAD_CONTRACT_DIR = os.path.join('static', 'contracts')
os.makedirs(UPLOAD_CONTRACT_DIR, exist_ok=True)
ALLOWED_CONTRACT_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}
# Hulpfunctie om bestands extensie te controleren
def allowed_contract_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_CONTRACT_EXTENSIONS


#Algoritme voor prijsadvies
from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import Kot, Boeking


DEFAULT_TOURIST_TAX_PER_PERSON_PER_NIGHT = 6.0  # fallbacktarief per persoon, per nacht
TOURIST_TAX_SETTING_KEY = 'tourist_tax_per_person_per_night'


def get_tourist_tax_amount():
    setting = SysteemInstelling.query.get(TOURIST_TAX_SETTING_KEY)
    if setting:
        try:
            value = float(setting.waarde)
            if value >= 0:
                return value
        except (TypeError, ValueError):
            pass
    return DEFAULT_TOURIST_TAX_PER_PERSON_PER_NIGHT


def save_tourist_tax_amount(new_value):
    setting = SysteemInstelling.query.get(TOURIST_TAX_SETTING_KEY)
    if not setting:
        setting = SysteemInstelling(sleutel=TOURIST_TAX_SETTING_KEY, waarde=str(new_value))
        db.session.add(setting)
    else:
        setting.waarde = str(new_value)
    db.session.commit()
    return new_value

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
            # Contracten die wachten op student
            contracten_te_ondertekenen = Contract.query.filter_by(
                student_id=gebruiker.student.gebruiker_id,
                status_contract='wachten_op_student'
            ).all()
            return render_template(
                'dashboard_student.html',
                koten=koten,
                inbox=inbox,
                naam=gebruiker.naam,
                rollen=rollen,
                actieve_rol=actieve_rol,
                contracten_te_ondertekenen=contracten_te_ondertekenen
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
        if 'gebruiker_id' not in session or session.get('rol') not in ['student', 'kotbaas', 'admin']:
            return redirect(url_for('login'))

        rol = session.get('rol')
        gebruiker = Gebruiker.query.get(session['gebruiker_id'])
        if not gebruiker:
            flash('Gebruiker niet gevonden.', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            # veilige parsing
            try:
                adres = request.form['adres'].strip()
                stad = request.form['stad'].strip()
                oppervlakte = float(request.form['oppervlakte'])
                aantal_slaapplaatsen = int(request.form['aantal_slaapplaatsen'])
                maandhuurprijs = float(request.form['maandhuurprijs'])
                egwkosten = float(request.form.get('egwkosten') or 0)
            except (KeyError, ValueError):
                flash('Ongeldige invoer — controleer getallen en verplichte velden.', 'error')
                return render_template('add_kot.html', rol=rol, gebruiker=gebruiker)

            eigen_keuken = True if request.form.get('eigen_keuken') else False
            eigen_sanitair = True if request.form.get('eigen_sanitair') else False

            # Kotbaas/beschrijving/foto
            beschrijving = None
            foto_url = ''
            if rol in ['kotbaas', 'admin']:
                beschrijving = request.form.get('beschrijving', '').strip() or None
                foto_url = request.form.get('foto', '').strip() or ''

            #Wanneer einddatum < begindatum niet alle velden leegmaken 
            #haal alle formulierdata
            form_data = request.form.to_dict()

            # probeer datums om te zetten
            startdatum_str = form_data.get('startdatum', '')
            einddatum_str = form_data.get('einddatum', '')

            try:
                startdatum = datetime.strptime(startdatum_str, "%Y-%m-%d")
                einddatum = datetime.strptime(einddatum_str, "%Y-%m-%d")
            except ValueError:
                flash("Datums ongeldig.", "error")
                # alleen datums leegmaken
                form_data['startdatum'] = ''
                form_data['einddatum'] = ''
                return render_template('add_kot.html', rol=rol, gebruiker=gebruiker, **form_data)

            if einddatum <= startdatum:
                flash("Einddatum moet later zijn dan startdatum.", "error")
                # alleen datums leegmaken
                form_data['startdatum'] = ''
                form_data['einddatum'] = ''
                return render_template('add_kot.html', rol=rol, gebruiker=gebruiker, **form_data)

            # Bepaal student_id en kotbaas_id
            student_id = None
            kotbaas_id = None

            if rol == 'student':
                kotbaas_voornaam = request.form.get('kotbaas_voornaam', '').strip()
                kotbaas_achternaam = request.form.get('kotbaas_achternaam', '').strip()
                if not kotbaas_voornaam or not kotbaas_achternaam:
                    flash('Vul voor- en achternaam van kotbaas in.', 'error')
                    return render_template('add_kot.html', rol=rol, gebruiker=gebruiker)
                kotbaas_naam = f"{kotbaas_voornaam} {kotbaas_achternaam}"
                kotbaas = Gebruiker.query.filter_by(naam=kotbaas_naam).first()
                if not kotbaas:
                    flash('Kotbaas niet gevonden.', 'error')
                    return render_template('add_kot.html', rol=rol, gebruiker=gebruiker)
                kotbaas_id = kotbaas.gebruiker_id
                student_id = gebruiker.gebruiker_id

            elif rol in ['kotbaas', 'admin']:
                # eigenaar velden voor kotbaas/admin
                eigenaar_voornaam = request.form.get('eigenaar_voornaam', '').strip()
                eigenaar_achternaam = request.form.get('eigenaar_achternaam', '').strip()
                if rol == 'kotbaas' and eigenaar_voornaam and eigenaar_achternaam:
                    gebruiker.naam = f"{eigenaar_voornaam} {eigenaar_achternaam}"

                # als kotbaas moet je studentnaam invullen
                student_naam = request.form.get('student_naam', '').strip()
                if not student_naam:
                    flash('Vul de studentnaam in.', 'error')
                    return render_template('add_kot.html', rol=rol, gebruiker=gebruiker)
                student = Gebruiker.query.filter_by(naam=student_naam).first()
                if not student:
                    flash('Student niet gevonden.', 'error')
                    return render_template('add_kot.html', rol=rol, gebruiker=gebruiker)
                student_id = student.gebruiker_id
                kotbaas_id = gebruiker.gebruiker_id if rol == 'kotbaas' else None

            # initiatiefnemer: duidelijke regels
            initiatiefnemer_checked = bool(request.form.get('initiatiefnemer'))
            if rol == 'student':
                initiatiefnemer = 'student' if initiatiefnemer_checked else 'kotbaas'
            elif rol == 'kotbaas':
                initiatiefnemer = 'kotbaas' if initiatiefnemer_checked else 'student'
            else:
                initiatiefnemer = 'kotbaas' if initiatiefnemer_checked else 'student'

            # bereken prijsadvies (optioneel)
            aangeraden_prijs = bereken_aangeraden_prijs(oppervlakte, aantal_slaapplaatsen, stad)
            if aangeraden_prijs:
                flash(f"Op basis van vergelijkbare koten: aanbevolen maandhuur €{aangeraden_prijs:.2f}", "info")
            else:
                flash("Geen vergelijkbare koten gevonden om prijsadvies te geven.", "info")

            # Maak en commit objecten in één transactie
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
            db.session.flush()  # zorgt dat kot.kot_id beschikbaar is zonder commit

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

        # GET
        return render_template('add_kot.html', rol=session.get('rol'), gebruiker=gebruiker)



    # Realtime prijsadvies route
    @app.route('/prijsadvies', methods=['POST'])
    def prijsadvies():
        data = request.get_json()
        oppervlakte = data.get('oppervlakte')
        slaapplaatsen = data.get('slaapplaatsen')
        stad = data.get('stad', None)

        if not oppervlakte or not slaapplaatsen:
            return {'advies': None}, 200

        try:
            oppervlakte = float(oppervlakte)
            slaapplaatsen = int(slaapplaatsen)
        except ValueError:
            return {'advies': None}, 200

        advies = bereken_aangeraden_prijs(oppervlakte, slaapplaatsen, stad)
        if advies is None:
            return {'advies': "Geen gelijkaardige koten aan dat van U"}, 200
        return {'advies': f"Op basis van gelijkaardige koten raden we een maandhuurprijs van €{advies:.2f} aan."}, 200


    
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

        # Contract wordt automatisch mee verwijderd door cascade op Kot.contract
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

            # Datums parsen
            try:
                startdatum = datetime.strptime(startdatum_str, "%Y-%m-%d")
                einddatum = datetime.strptime(einddatum_str, "%Y-%m-%d")
                if einddatum <= startdatum:
                    flash('Einddatum moet later zijn dan startdatum.', 'error')
                    fouten = True
            except ValueError:
                flash('Ongeldige start- of einddatum.', 'error')
                fouten = True

            # Aantal personen valideren
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

            # STOP en toon formulier opnieuw als er fouten zijn
            if fouten:
                return render_template(
                    'boek.html',
                    kot=kot,
                    default_start=startdatum_str or default_start.strftime('%Y-%m-%d'),
                    default_end=einddatum_str or default_end.strftime('%Y-%m-%d'),
                    form_data=request.form,
                    huurder=huurder
                )

            # 1) Niet eigen kot huren (student of kotbaas)
            huurder_id = huurder.gebruiker_id
            is_student_eigen_kot = (kot.student_id == huurder_id)
            is_kotbaas_eigen_kot = (kot.kotbaas_id == huurder_id)
            if is_student_eigen_kot or is_kotbaas_eigen_kot:
                flash('Je kan je eigen kot niet huren.', 'error')
                return render_template(
                    'boek.html',
                    kot=kot,
                    default_start=startdatum_str or default_start.strftime('%Y-%m-%d'),
                    default_end=einddatum_str or default_end.strftime('%Y-%m-%d'),
                    form_data=request.form,
                    huurder=huurder
                )

            # 2) Gevraagde periode moet binnen beschikbaarheid liggen
            #    (veronderstelt een Beschikbaarheid-tabel met kot_id, startdatum, einddatum)
            beschikbare = Beschikbaarheid.query.filter_by(kot_id=kot.kot_id).all()
            # we zoeken minstens één beschikbaarheidsrecord dat de volledige periode dekt
            volledig_beschikbaar = False
            for b in beschikbare:
                # b.startdatum en b.einddatum zijn Date; startdatum/einddatum hier zijn datetime
                b_start = datetime.combine(b.startdatum, datetime.min.time())
                b_end = datetime.combine(b.einddatum, datetime.min.time())
                if b_start <= startdatum and b_end >= einddatum:
                    volledig_beschikbaar = True
                    break

            if not volledig_beschikbaar:
                flash('Dit kot is niet beschikbaar in de gekozen periode.', 'error')
                return render_template(
                    'boek.html',
                    kot=kot,
                    default_start=startdatum_str or default_start.strftime('%Y-%m-%d'),
                    default_end=einddatum_str or default_end.strftime('%Y-%m-%d'),
                    form_data=request.form,
                    huurder=huurder
                )

            # Prijsberekening
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

        # GET: leeg formulier tonen
        return render_template(
            'boek.html',
            kot=kot,
            default_start=default_start.strftime('%Y-%m-%d'),
            default_end=default_end.strftime('%Y-%m-%d'),
            form_data={},
            huurder=huurder
        )



    @app.route('/boeking/<int:boeking_id>/betaling', methods=['GET', 'POST'])
    def betaling_overzicht(boeking_id):
        if 'gebruiker_id' not in session or session.get('rol') != 'huurder':
            return redirect(url_for('login'))

        boeking = Boeking.query.get_or_404(boeking_id)

        # Zeker zijn dat deze boeking van de ingelogde huurder is
        if boeking.gebruiker_id != session['gebruiker_id']:
            flash("Je mag deze betaling niet uitvoeren.", "error")
            return redirect(url_for('dashboard'))

        # Totale prijs berekenen (eenvoudig: maandhuur * aantal maanden)
        # Of gebruik jouw bestaande berekening indien je die hebt.
        start = boeking.startdatum
        eind = boeking.einddatum
        dagen = (eind - start).days or 1
        # voorbeeld: prijs per dag = maandhuur / 30
        prijs_per_dag = boeking.kot.maandhuurprijs / 30
        totaal_bedrag = round(dagen * prijs_per_dag, 2)

        if request.method == 'POST':
            # Hier 'simuleer' je de betaling: status op betaald
            boeking.status_boeking = "Betaald"
            db.session.commit()
            flash("Je betaling is geregistreerd.", "success")
            return redirect(url_for('dashboard'))

        rekeningnummer = "BE12 3456 7890 1234"  # Gitoo-rekeningnummer
        tenaamstelling = "Gitoo BV"

        return render_template(
            'betaling_overzicht.html',
            boeking=boeking,
            totaal_bedrag=totaal_bedrag,
            rekeningnummer=rekeningnummer,
            tenaamstelling=tenaamstelling
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
        koten = Kot.query.filter_by(kotbaas_id=kotbaas.gebruiker_id).all()
        pending_koten = Kot.query.filter_by(kotbaas_id=kotbaas.gebruiker_id, goedgekeurd=False).all()

        # Contracten die wachten op kotbaas
        contracten_te_ondertekenen = Contract.query.filter_by(
            kotbaas_id=kotbaas.gebruiker_id,
            status_contract='wachten_op_kotbaas'
        ).all()

        return render_template(
            'dashboard_kotbaas.html',
            naam=kotbaas.gebruiker.naam,
            koten=koten,
            pending_koten=pending_koten,
            contracten_te_ondertekenen=contracten_te_ondertekenen
        )


    @app.route('/kot/<int:kot_id>/contract/kotbaas', methods=['GET', 'POST'])
    def contract_kotbaas(kot_id):
        if 'gebruiker_id' not in session or session.get('rol') != 'kotbaas':
            return redirect(url_for('login'))

        kot = Kot.query.get_or_404(kot_id)
        if kot.kotbaas_id != session['gebruiker_id']:
            flash("Je mag alleen contracten voor je eigen koten beheren.", "error")
            return redirect(url_for('dashboard_kotbaas'))

        contract = Contract.query.filter_by(kot_id=kot.kot_id).first()
        if not contract:
            flash("Er is nog geen contract voor dit kot aangemaakt.", "error")
            return redirect(url_for('dashboard_kotbaas'))

        if request.method == 'POST':
            file = request.files.get('contract_file')
            if not file or not file.filename:
                flash("Upload een bestand.", "error")
                return redirect(url_for('contract_kotbaas', kot_id=kot_id))

            if not allowed_contract_file(file.filename):
                flash("Bestandstype niet toegestaan. Gebruik pdf, png, jpg of jpeg.", "error")
                return redirect(url_for('contract_kotbaas', kot_id=kot_id))

            filename = secure_filename(file.filename)
            unique_name = f"kot{kot_id}_kotbaas_{int(time.time())}{os.path.splitext(filename)[1].lower()}"
            save_path = os.path.join(app.static_folder, 'contracts')
            os.makedirs(save_path, exist_ok=True)
            full_path = os.path.join(save_path, unique_name)
            file.save(full_path)

            static_rel = f"contracts/{unique_name}"
            contract.pad_kotbaas = url_for('static', filename=static_rel)
            contract.status_contract = 'wachten_op_student'
            db.session.commit()

            flash("Ondertekend contract succesvol geüpload. De student kan nu ondertekenen.", "success")
            return redirect(url_for('dashboard_kotbaas'))

        return render_template('contract_kotbaas_upload.html', kot=kot, contract=contract)

    @app.route('/kot/<int:kot_id>/contract/student', methods=['GET', 'POST'])
    def contract_student(kot_id):
        if 'gebruiker_id' not in session or session.get('rol') != 'student':
            return redirect(url_for('login'))

        kot = Kot.query.get_or_404(kot_id)
        contract = Contract.query.filter_by(kot_id=kot.kot_id).first()

        if not contract or contract.student_id != session['gebruiker_id']:
            flash("Je mag dit contract niet beheren.", "error")
            return redirect(url_for('dashboard'))

        if contract.status_contract not in ('wachten_op_student', 'compleet'):
            flash("Dit contract wacht nog op de kotbaas.", "error")
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            file = request.files.get('contract_file')
            if not file or not file.filename:
                flash("Upload een bestand.", "error")
                return redirect(url_for('contract_student', kot_id=kot_id))

            if not allowed_contract_file(file.filename):
                flash("Bestandstype niet toegestaan. Gebruik pdf, png, jpg of jpeg.", "error")
                return redirect(url_for('contract_student', kot_id=kot_id))

            filename = secure_filename(file.filename)
            unique_name = f"kot{kot_id}_student_{int(time.time())}{os.path.splitext(filename)[1].lower()}"
            save_path = os.path.join(app.static_folder, 'contracts')
            os.makedirs(save_path, exist_ok=True)
            full_path = os.path.join(save_path, unique_name)
            file.save(full_path)

            static_rel = f"contracts/{unique_name}"
            contract.pad_student = url_for('static', filename=static_rel)
            contract.status_contract = 'compleet'
            db.session.commit()

            flash("Je ondertekende contract is geüpload. Gitoo kan het nu verwerken.", "success")
            return redirect(url_for('dashboard'))

        return render_template('contract_student_upload.html', kot=kot, contract=contract)

    
    @app.route('/dashboard_admin')
    def dashboard_admin():
        if 'rol' not in session or session['rol'] != 'admin':
            return redirect(url_for('login'))

        zoekterm = request.args.get('zoekterm', '').strip()
        status_boeking = request.args.get('status_boeking', '').strip()
        aantal_personen = request.args.get('aantal_personen', '').strip()
        periode_start = request.args.get('periode_start', '').strip()
        periode_eind = request.args.get('periode_eind', '').strip()

        filters = {
            'zoekterm': zoekterm,
            'status_boeking': status_boeking,
            'aantal_personen': aantal_personen,
            'periode_start': periode_start,
            'periode_eind': periode_eind,
        }

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

        if status_boeking:
            boeking_query = boeking_query.filter(Boeking.status_boeking == status_boeking)

        if aantal_personen:
            try:
                ap = int(aantal_personen)
                boeking_query = boeking_query.filter(Boeking.aantal_personen == ap)
            except ValueError:
                pass

        # Periode filter
        if periode_start or periode_eind:
            try:
                start_dt = datetime.strptime(periode_start, "%Y-%m-%d") if periode_start else None
                eind_dt = datetime.strptime(periode_eind, "%Y-%m-%d") if periode_eind else None
                if start_dt and eind_dt:
                    boeking_query = boeking_query.filter(
                        Boeking.startdatum >= start_dt,
                        Boeking.einddatum <= eind_dt
                    )
                elif start_dt:
                    boeking_query = boeking_query.filter(Boeking.startdatum >= start_dt)
                elif eind_dt:
                    boeking_query = boeking_query.filter(Boeking.einddatum <= eind_dt)
            except ValueError:
                pass

        boeking_query = boeking_query.order_by(Boeking.startdatum.asc())
        boekingen = boeking_query.all()
        return render_template('admin_booking_overview.html',
                            boekingen=boekingen,
                            filters=filters)


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
        tourist_tax_amount = get_tourist_tax_amount()

        for kot in koten:
            maandhuur = float(kot.maandhuurprijs or 0)
            egwkosten = float(kot.egwkosten or 0)
            totale_maandlast = maandhuur + egwkosten
            omzet_per_nacht = totale_maandlast / 30 if totale_maandlast else 0
            totale_omzet = 0.0
            totale_toeristenbelasting = 0.0

            for boeking in kot.boekingen:
                totaalprijs = float(boeking.totaalprijs or 0)
                totale_omzet += totaalprijs
                personen = int(boeking.aantal_personen or 1)
                nachten = 0
                if boeking.startdatum and boeking.einddatum:
                    delta_dagen = (boeking.einddatum.date() - boeking.startdatum.date()).days
                    nachten = max(delta_dagen, 0)
                totale_toeristenbelasting += personen * nachten * tourist_tax_amount

            egw_aandeel_omzet = totale_omzet * (egwkosten / totale_maandlast) if totale_maandlast else 0
            egw_per_nacht = egwkosten / 30 if egwkosten else 0

            kot_statistieken[kot.kot_id] = {
                'omzet_per_nacht': omzet_per_nacht,
                'totale_omzet': totale_omzet,
                'toeristenbelasting': totale_toeristenbelasting,
                'omzet_na_belasting': max(totale_omzet - totale_toeristenbelasting, 0.0),
                'egw_per_maand': egwkosten,
                'egw_per_nacht': egw_per_nacht,
                'egw_aandeel_omzet': egw_aandeel_omzet,
            }

        return render_template(
            'admin_kot_list.html',
            koten=koten,
            kot_statistieken=kot_statistieken,
            tourist_tax_amount=tourist_tax_amount,
            zoekterm=zoekterm
        )

    @app.route('/admin/tourist_tax', methods=['POST'])
    def update_tourist_tax():
        if session.get('rol') != 'admin':
            return redirect(url_for('login'))

        raw_value = request.form.get('tourist_tax_amount', '').strip().replace(',', '.')
        try:
            new_value = float(raw_value)
            if new_value < 0:
                raise ValueError
        except ValueError:
            flash('Voer een geldige positieve waarde in voor de toeristenbelasting.', 'error')
            return redirect(url_for('dashboard_admin_koten'))

        rounded_value = round(new_value, 2)
        save_tourist_tax_amount(rounded_value)
        flash(f'Toeristenbelasting bijgewerkt naar €{rounded_value:.2f} per persoon per nacht.', 'success')
        return redirect(url_for('dashboard_admin_koten'))

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
    
    @app.route('/dashboard_admin_contracten')
    def dashboard_admin_contracten():
        if 'rol' not in session or session['rol'] != 'admin':
            return redirect(url_for('login'))

        status_filter = request.args.get('status', '').strip()
        query = Contract.query.options(
            joinedload(Contract.kot),
            joinedload(Contract.student).joinedload(Student.gebruiker),
            joinedload(Contract.kotbaas).joinedload(Kotbaas.gebruiker)
        )

        if status_filter:
            query = query.filter(Contract.status_contract == status_filter)

        contracten = query.all()

        return render_template(
            'admin_contract_list.html',
            contracten=contracten,
            status_filter=status_filter
        )


    @app.route('/boeking/<int:boeking_id>/pay', methods=['POST'])
    def pay_boeking(boeking_id):
        """Markeer een boeking van de huurder als volledig betaald."""
        if 'gebruiker_id' not in session:
            return redirect(url_for('login'))

        gebruiker = Gebruiker.query.get(session['gebruiker_id'])
        if not gebruiker or not gebruiker.huurder:
            flash('Deze actie is alleen voor huurders.', 'error')
            return redirect(url_for('dashboard'))

        boeking = Boeking.query.get_or_404(boeking_id)
        if boeking.gebruiker_id != gebruiker.huurder.gebruiker_id:
            flash('Je kan enkel je eigen boekingen betalen.', 'error')
            return redirect(url_for('dashboard'))

        status = (boeking.status_boeking or '').lower()
        if 'geannuleerd' in status:
            flash('Geannuleerde boekingen kunnen niet betaald worden.', 'info')
            return redirect(url_for('dashboard'))
        if 'betaald' in status:
            flash('Deze boeking was al als betaald gemarkeerd.', 'info')
            return redirect(url_for('dashboard'))

        boeking.status_boeking = 'betaald (hele termijn)'
        db.session.commit()
        flash('Bedankt! De volledige betaling is geregistreerd.', 'success')
        return redirect(url_for('dashboard'))

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
    
    @app.route('/approve_kot/<int:kot_id>', methods=['POST']) #Kotbaas moet eerst kot goedkeuren
    def approve_kot(kot_id):
        kot = Kot.query.get_or_404(kot_id)
        if 'gebruiker_id' not in session or session.get('rol') != 'kotbaas' or session['gebruiker_id'] != kot.kotbaas_id:
            flash("Je mag alleen je eigen koten goedkeuren.", "error")
            return redirect(url_for('dashboard_kotbaas'))

        # Kot zichtbaar maken
        kot.goedgekeurd = True
        db.session.commit()

        # Contract aanmaken indien nog niet bestaand
        bestaand_contract = Contract.query.filter_by(kot_id=kot.kot_id).first()
        if not bestaand_contract:
            contract = Contract(
                kot_id=kot.kot_id,
                student_id=kot.student_id,
                kotbaas_id=kot.kotbaas_id,
                status_contract='wachten_op_kotbaas'
            )
            db.session.add(contract)
            db.session.commit()
            flash("Kot goedgekeurd. Er is een contractopdracht aangemaakt in je dashboard.", "success")
        else:
            flash("Kot goedgekeurd. Er bestond al een contract voor dit kot.", "info")

        return redirect(url_for('dashboard_kotbaas'))


    
