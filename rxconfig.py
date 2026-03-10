import os
import reflex as rx

config = rx.Config(
    app_name="cont_synth",
    api_url=os.environ.get("API_URL", "http://localhost:8000"),
    db_url=os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/contsynth"
    ),
    show_built_with_reflex=False,
    stylesheets=["/style.css"],
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)