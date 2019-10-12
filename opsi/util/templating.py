from os.path import realpath

from starlette.templating import Jinja2Templates, _TemplateResponse


def TemplateFolder(directory):
    """Usage:
    self.templates = TemplateFolder("path")
    self.app.add_route(self.templates("file.html", key=value))
    """

    template_reader = Jinja2Templates(realpath(directory))

    def create_template(filename, **kwargs):
        def endpoint(request):
            return template_reader.TemplateResponse(
                filename, {"request": request, **kwargs}
            )

        return endpoint

    return create_template


def LiteralTemplate(template, **kwargs):
    """Usage:
    self.app.add_route(LiteralTemplate("<html>...", key=value))
    """

    def endpoint(request):
        return _TemplateResponse(template, {"request": request, **kwargs})

    return endpoint
