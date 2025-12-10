from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import db, Kot, Boeking


def bereken_aangeraden_prijs(oppervlakte, slaapplaatsen, stad=None, window_days=180):
    """
    Berekening aanbevolen maandhuurprijs.
    - vergelijkbaar = oppervlakte ±5 m², zelfde aantal slaapplaatsen, optioneel zelfde stad
    - houdt rekening met verhuuractiviteit (laatste boeking binnen window_days)
    - returned float rounded(.,2) of None als geen vergelijkbare koten
    """

    #Typecontrole
    try:
        oppervlakte = float(oppervlakte)
        slaapplaatsen = int(slaapplaatsen)
    except (ValueError, TypeError):
        return None  # Ongeldige invoer → geen advies

    #Bereken de minimale en maximale oppervlakte voor vergelijkbare koten
    lower_area = oppervlakte - 5  # 5 m² kleiner
    upper_area = oppervlakte + 5  # 5 m² groter

    #Basisfilter: selecteer koten met vergelijkbare oppervlakte, zelfde aantal slaapplaatsen, en maandhuurprijs bekend
    base_query = Kot.query.filter(
        Kot.oppervlakte.between(lower_area, upper_area),
        Kot.aantal_slaapplaatsen == slaapplaatsen,
        Kot.maandhuurprijs.isnot(None)
    )

    #Optioneel filter op stad
    if stad and stad.strip():
        base_query = base_query.filter(Kot.stad.ilike(f"%{stad}%"))

    #Bereken gemiddelde maandhuurprijs van de vergelijkbare koten
    gemiddelde_prijs = base_query.with_entities(func.avg(Kot.maandhuurprijs)).scalar()
    if not gemiddelde_prijs:
        return None  # Geen vergelijkbare koten → geen advies
    gemiddelde_prijs = float(gemiddelde_prijs)

    #Subquery: zoek laatste boekingen per kot (voor recente verhuuractiviteit)
    subq = (
        db.session.query(
            Boeking.kot_id,
            func.max(Boeking.einddatum).label("laatste_eind")
        )
        .filter(Boeking.kot_id.in_([k.kot_id for k in base_query.all()]))  # alleen vergelijkbare koten
        .group_by(Boeking.kot_id)
        .subquery()
    )

    #Haal de datums van de laatste boekingen op
    laatste_datums = [row.laatste_eind for row in db.session.query(subq.c.laatste_eind).all()]

    #Bereken cutoff-datum voor recente verhuur
    cutoff = datetime.now() - timedelta(days=window_days)
    recent = sum(1 for d in laatste_datums if d and d >= cutoff)

    # Bereken totaal aantal vergelijkbare koten
    totaal = base_query.count()

    #Percentage recent verhuurd
    percentage_recent = recent / totaal if totaal > 0 else 1

    #Pas de prijs aan: als minder dan 50% recent gehuurd, 10% korting
    if percentage_recent < 0.5:
        aanbevolen = gemiddelde_prijs * 0.90
    else:
        aanbevolen = gemiddelde_prijs

    #Rond af en geef advies terug
    return round(aanbevolen, 2)
