from . import db

class Student(db.Model):
    __tablename__ = 'student'
    student_id = db.Column(db.Integer, primary_key=True)
    naam = db.Column(db.String)
    email = db.Column(db.String, unique=True, nullable=False)
    telefoon = db.Column(db.String)
    universiteit = db.Column(db.String)

class Kot(db.Model):
    __tablename__ = 'kot'
    kot_id = db.Column(db.Integer, primary_key=True)
    adres = db.Column(db.String)
    stad = db.Column(db.String)
    oppervlakte = db.Column(db.Integer)
    aantal_slaapplaatsen = db.Column(db.Integer)
    prijs_per_nacht = db.Column(db.Numeric)
    eigen_keuken = db.Column(db.Boolean)
    eigen_sanitair = db.Column(db.Boolean)
    egw_kosten = db.Column(db.Numeric)
    goedgekeurd = db.Column(db.Boolean)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'))
    student = db.relationship('Student', backref='koten')

class Huurder(db.Model):
    __tablename__ = 'huurder'
    huurder_id = db.Column(db.Integer, primary_key=True)
    naam = db.Column(db.String)
    email = db.Column(db.String, unique=True, nullable=False)
    telefoon = db.Column(db.String)

class Beschikbaarheid(db.Model):
    __tablename__ = 'beschikbaarheid'
    beschikbaarheid_id = db.Column(db.Integer, primary_key=True)
    kot_id = db.Column(db.Integer, db.ForeignKey('kot.kot_id'))
    start_datum = db.Column(db.Date)
    eind_datum = db.Column(db.Date)
    kot = db.relationship('Kot', backref='beschikbaarheden')

class Boeking(db.Model):
    __tablename__ = 'boeking'
    boeking_id = db.Column(db.Integer, primary_key=True)
    kot_id = db.Column(db.Integer, db.ForeignKey('kot.kot_id'))
    huurder_id = db.Column(db.Integer, db.ForeignKey('huurder.huurder_id'))
    start_datum = db.Column(db.Date)
    eind_datum = db.Column(db.Date)
    totaal_prijs = db.Column(db.Numeric)
    kot = db.relationship('Kot', backref='boekingen')
    huurder = db.relationship('Huurder', backref='boekingen')