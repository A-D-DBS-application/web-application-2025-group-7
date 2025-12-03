from . import db
from datetime import datetime

class Gebruiker(db.Model):
    __tablename__ = 'gebruiker'
    gebruiker_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    naam = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    telefoon = db.Column(db.String)
    type = db.Column(db.String)  # 'student', 'huurder', 'kotbaas'
    aangemaakt_op = db.Column(db.DateTime)

    # Relationships
    student = db.relationship('Student', backref='gebruiker', uselist=False)
    huurder = db.relationship('Huurder', backref='gebruiker', uselist=False)
    # bookings and koten handled separately

class Student(db.Model):
    __tablename__ = 'student'
    gebruiker_id = db.Column(db.Integer, db.ForeignKey('gebruiker.gebruiker_id'), primary_key=True)
    universiteit = db.Column(db.String)
    initiatiefnemer = db.Column(db.Boolean, default=False)

class Huurder(db.Model):
    __tablename__ = 'huurder'
    gebruiker_id = db.Column(db.Integer, db.ForeignKey('gebruiker.gebruiker_id'), primary_key=True)
    voorkeuren = db.Column(db.Text, default="")
    gesproken_taal = db.Column(db.String)

    # One huurder can have many bookings
    boekingen = db.relationship('Boeking', backref='huurder', lazy=True)

class Kot(db.Model):
    __tablename__ = 'kot'
    kot_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.gebruiker_id'))
    kotbaas_id = db.Column(db.Integer, db.ForeignKey('kotbaas.gebruiker_id'))
    initiatiefnemer = db.Column(db.String)  # 'student' of 'kotbaas'
    adres = db.Column(db.String, nullable=False)
    stad = db.Column(db.String, nullable=False)
    oppervlakte = db.Column(db.Integer)
    aantal_slaapplaatsen = db.Column(db.Integer)
    maandhuurprijs = db.Column(db.Float, nullable=False)
    brandveiligheidsconformiteit = db.Column(db.Boolean, default=True)
    eigen_keuken = db.Column(db.Boolean, default=False)
    eigen_sanitair = db.Column(db.Boolean, default=False)
    egwkosten = db.Column(db.Float)
    goedgekeurd = db.Column(db.Boolean, default=False)
    beschrijving = db.Column(db.Text)
    foto = db.Column(db.Text)

    # Relationships
    beschikbaarheden = db.relationship('Beschikbaarheid', backref='kot', lazy=True)
    boekingen = db.relationship('Boeking', backref='kot', lazy=True)
    student = db.relationship('Student', backref='koten', foreign_keys=[student_id])
    kotbaas = db.relationship('Kotbaas', backref='koten', foreign_keys=[kotbaas_id])

class Beschikbaarheid(db.Model):
    __tablename__ = "beschikbaarheid"
    beschikbaarheid_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kot_id = db.Column(db.Integer, db.ForeignKey('kot.kot_id'), nullable=False)
    startdatum = db.Column(db.Date, nullable=False)
    einddatum = db.Column(db.Date, nullable=False)
    status_beschikbaarheid = db.Column(db.String(50), default="beschikbaar")

class Boeking(db.Model):
    __tablename__ = 'boeking'
    boeking_id = db.Column(db.Integer, primary_key=True)
    gebruiker_id = db.Column(db.Integer, db.ForeignKey('huurder.gebruiker_id'))
    kot_id = db.Column(db.Integer, db.ForeignKey('kot.kot_id'))
    startdatum = db.Column(db.DateTime, nullable=False)
    einddatum = db.Column(db.DateTime, nullable=False)
    totaalprijs = db.Column(db.Numeric)
    status_boeking = db.Column(db.String)
    aantal_personen = db.Column(db.Integer, nullable=False, default=1)

class Kotbaas(db.Model):
    __tablename__ = 'kotbaas'
    gebruiker_id = db.Column(db.Integer, db.ForeignKey('gebruiker.gebruiker_id'), primary_key=True)
    initiatiefnemer = db.Column(db.Boolean, default=False)
    gebruiker = db.relationship('Gebruiker', backref='kotbaas', uselist=False)

class Contract(db.Model):
    __tablename__ = 'contract'

    contract_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Koppeling aan kot + partijen
    kot_id = db.Column(db.Integer, db.ForeignKey('kot.kot_id'), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.gebruiker_id'), nullable=False)
    kotbaas_id = db.Column(db.Integer, db.ForeignKey('kotbaas.gebruiker_id'), nullable=False)
    # Status: 'wachten_op_kotbaas', 'wachten_op_student', 'compleet'
    status_contract = db.Column(db.String(50), nullable=False, default='wachten_op_kotbaas')
    # Paden naar uploads (PDF/scan)
    pad_contract_sjabloon = db.Column(db.String)      # optioneel: gegenereerd basiscontract
    pad_kotbaas = db.Column(db.String)                # door kotbaas ondertekend
    pad_student = db.Column(db.String)                # door student ondertekend
    aangemaakt_op = db.Column(db.DateTime, default=datetime.utcnow)
    laatst_bijgewerkt_op = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    # Relaties
    kot = db.relationship('Kot', backref=db.backref('contract', uselist=False))
    student = db.relationship('Student', backref='contracten')
    kotbaas = db.relationship('Kotbaas', backref='contracten')
