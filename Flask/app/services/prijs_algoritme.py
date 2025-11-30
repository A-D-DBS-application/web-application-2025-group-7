from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import Kot, Boeking

def bereken_aangeraden_prijs(oppervlakte, slaapplaatsen, stad=None):
    """
    Berekent een aanbevolen maandhuurprijs op basis van vergelijkbare koten.
    - vergelijkbaar = oppervlakte ±10%, zelfde aantal slaapplaatsen, optioneel zelfde stad
    - houdt rekening met verhuuractiviteit: koten die lang leeg staan drukken advies omlaag
    - verandert NOOIT prijzen van koten zelf
    """
    lower_area = int(oppervlakte * 0.9)
    upper_area = int(oppervlakte * 1.1)

    vergelijkbaar_query = Kot.query.filter(
        Kot.oppervlakte.between(lower_area, upper_area),
        Kot.aantal_slaapplaatsen == slaapplaatsen,
        Kot.maandhuurprijs.isnot(None)
    )

    if stad:
        vergelijkbaar_query = vergelijkbaar_query.filter(Kot.stad.ilike(f"%{stad}%"))

    vergelijkbare_koten = vergelijkbaar_query.all()
    if not vergelijkbare_koten:
        return None

    gemiddelde_prijs = vergelijkbaar_query.with_entities(func.avg(Kot.maandhuurprijs)).scalar()
    if gemiddelde_prijs is None:
        return None

    gemiddelde_prijs = float(gemiddelde_prijs)

    # Controle verhuuractiviteit
    cutoff = datetime.now() - timedelta(days=180)  # 6 maanden
    recent_gehuurd = 0
    totaal = len(vergelijkbare_koten)

    for k in vergelijkbare_koten:
        laatste_boeking = Boeking.query.filter_by(kot_id=k.kot_id).order_by(Boeking.einddatum.desc()).first()
        if laatste_boeking and laatste_boeking.einddatum and laatste_boeking.einddatum >= cutoff:
            recent_gehuurd += 1

    percentage_recent = recent_gehuurd / totaal if totaal > 0 else 1

    # Indien veel koten lang stil staan → advies omlaag
    if percentage_recent < 0.5:
        aanbevolen = gemiddelde_prijs * 0.90
    else:
        aanbevolen = gemiddelde_prijs

    return round(aanbevolen, 2)
