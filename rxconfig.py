import reflex as rx

config = rx.Config(
    app_name="cont_synth",
    api_url="http://catalyst.local:8000",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)