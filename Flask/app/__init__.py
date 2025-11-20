from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect

db = SQLAlchemy()

def format_phone_number(value):
    if not value:
        return ""
    raw = str(value).strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return raw
    parts = []
    has_plus = raw.startswith("+")
    if has_plus:
        country_len = 2 if len(digits) > 4 else len(digits)
        parts.append(f"+{digits[:country_len]}")
        remainder = digits[country_len:]
    else:
        remainder = digits
    if remainder:
        parts.append(remainder[:3])
        remainder = remainder[3:]
        while remainder:
            parts.append(remainder[:2])
            remainder = remainder[2:]
    return " ".join(parts)

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    db.init_app(app)
    app.add_template_filter(format_phone_number, 'format_phone')

    # Import and register your routes
    from . import routes
    routes.register_routes(app)

    with app.app_context():
        db.create_all()
        # Ensure new columns exist without full migration setup (one-off safety)
        try:
            inspector = inspect(db.engine)
            kot_columns = [col['name'] for col in inspector.get_columns('kot')]
            if 'beschrijving' not in kot_columns:
                db.session.execute(text('ALTER TABLE kot ADD COLUMN beschrijving TEXT'))
                db.session.commit()

            boeking_columns = [col['name'] for col in inspector.get_columns('boeking')]
            if 'aantal_personen' not in boeking_columns:
                db.session.execute(text('ALTER TABLE boeking ADD COLUMN aantal_personen INTEGER NOT NULL DEFAULT 1'))
                db.session.commit()

            engine_name = db.engine.url.get_backend_name()
            if engine_name.startswith('postgresql'):
                seq_name = db.session.execute(
                    text("SELECT pg_get_serial_sequence('boeking', 'boeking_id')")
                ).scalar()
                if seq_name:
                    max_id = db.session.execute(
                        text('SELECT COALESCE(MAX(boeking_id), 0) FROM boeking')
                    ).scalar()
                    db.session.execute(
                        text('SELECT setval(to_regclass(:seq_name), :value, true)')
                        .bindparams(seq_name=seq_name, value=max_id)
                    )
                    db.session.commit()
        except Exception:
            # Silently ignore to avoid breaking startup if inspection fails
            pass

    return app
