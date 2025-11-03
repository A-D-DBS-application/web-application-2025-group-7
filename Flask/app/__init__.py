from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Goed gedaan, Ward. Dit is Flask!"

    return app
