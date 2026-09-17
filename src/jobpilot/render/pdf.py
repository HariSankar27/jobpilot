from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader("jobpilot", "render/templates"), autoescape=select_autoescape()
)


def render_resume(candidate: dict, bullets: list[str], out_path: str) -> str:
    # ponytail: lazy import - weasyprint needs system Pango/GTK libs that aren't on
    # every dev machine (present in the Docker image and CI runner).
    from weasyprint import HTML

    html = env.get_template("resume.html").render(candidate=candidate, bullets=bullets)
    HTML(string=html).write_pdf(out_path)
    return out_path
