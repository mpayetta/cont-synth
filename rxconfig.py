import reflex as rx

config = rx.Config(
    app_name="cont_synth",
    api_url="http://192.168.68.60:8000",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)