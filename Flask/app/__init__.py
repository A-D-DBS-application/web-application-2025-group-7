from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    db.init_app(app)

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
        except Exception:
            # Silently ignore to avoid breaking startup if inspection fails
            pass

    return app