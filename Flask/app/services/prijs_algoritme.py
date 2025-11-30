from datetime import datetime

def bereken_aangeraden_prijs(nieuw_kot, vergelijkbare_koten):
    """
    nieuw_kot: het kot dat net wordt toegevoegd
    vergelijkbare_koten: lijst met Kot-objecten
    """

    if not vergelijkbare_koten:
        return None

    prijzen = []

    for kot in vergelijkbare_koten:
        prijs = kot.maandhuurprijs

        # 1. check hoe lang het kot niet verhuurd is
        laatste_einddatum = None

        for b in kot.beschikbaarheden:
            if laatste_einddatum is None or b.einddatum > laatste_einddatum:
                laatste_einddatum = b.einddatum

        # 2. Als laatste verhuurperiode lang geleden is → slimmer afprijzen
        if laatste_einddatum:
            dagen_geen_huur = (datetime.now().date() - laatste_einddatum).days

            if dagen_geen_huur > 60:
                prijs *= 0.90   # 10% daling

            if dagen_geen_huur > 120:
                prijs *= 0.80   # 20% daling

        prijzen.append(prijs)

    # 3. gemiddelde prijs nemen
    gemiddelde = sum(prijzen) / len(prijzen)

    return round(gemiddelde, 2)
