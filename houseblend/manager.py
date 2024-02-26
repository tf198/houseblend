import os
import glob
from datetime import datetime
import json

from flask import Flask, render_template, request, Response, send_from_directory

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='hfdjioewvbr98436b7t98v4b3vt84b3t8cnbq85e71vbu98c7qpv',
        BASE_DIR='.'
    )

    if test_config is not None:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    @app.get('/app')
    def get_app():
        return render_template('app.html')
    
    from . import api
    app.register_blueprint(api.create_bp(app.config))

    return app

def run_app():
    app = create_app()
    app.run()

if __name__ == '__main__':
    run_app()