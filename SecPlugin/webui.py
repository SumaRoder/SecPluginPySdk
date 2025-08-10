import logging
import os
import flask
from flask import Flask, render_template

class WebUI:
    """
    WebUI
    Author: SumaRoder
    """

    def __init__(self, plugin):
        self.plugin = plugin
        self.app = self._setup_app()
        self._setup_logging()

    def _setup_logging(self):
        self.app.logger.disabled = True
        logging.getLogger('werkzeug').disabled = True
        logging.getLogger('flask').disabled = True

    def _setup_app(self) -> flask.Flask:
        template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
        static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "assets")
        
        app = Flask(__name__, 
                   template_folder=template_folder,
                   static_folder=static_folder, 
                   static_url_path="/assets")

        @app.route("/")
        def index():
            return render_template("index.html")

        @app.route("/<path:subpath>")
        def catch_all(subpath):
            return render_template("index.html")

        return app

    def start(self):
        self.app.run(host="0.0.0.0", 
                    port=24809,
                    debug=False, 
                    use_reloader=False)
