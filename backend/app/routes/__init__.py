"""Route blueprints — HTTP layer only. Business logic lives in services."""

from app.routes import admin, auth, pages, recruiters, shared, students


def register_blueprints(app):
    app.register_blueprint(pages.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(shared.bp)
    app.register_blueprint(students.bp)
    app.register_blueprint(recruiters.bp)
    app.register_blueprint(admin.bp)
