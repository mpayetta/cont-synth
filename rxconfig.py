import os
import reflex as rx

config = rx.Config(
    app_name="cont_synth",
    api_url=os.environ.get("API_URL", "http://localhost:8000"),
    prerender=False,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)