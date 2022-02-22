import os
from os import listdir
import collections
from os.path import isfile, join
from urllib.parse import parse_qs
from keyword import iskeyword
import warnings


def warning_message(message, category, filename, lineno, line=None):
    return f"{category.__name__}:\n {message} \n"


warnings.formatwarning = warning_message

PAGE_CONTAINER = ""
PAGE_REGISTRY = collections.OrderedDict()


def get_page_container():
    return PAGE_CONTAINER


def get_page_registry():
    return PAGE_REGISTRY


def _infer_image(module):
    """
    Return:
    - A page specific image: `assets/<title>.<extension>` is used, e.g. `assets/weekly_analytics.png`
    - A generic app image at `assets/app.<extension>`
    - A logo at `assets/logo.<extension>`
    """
    valid_extensions = ["apng", "avif", "gif", "jpeg", "png", "webp"]
    page_id = module.split(".")[-1]
    files_in_assets = []
    # todo need to check for app.get_assets_url instead?
    if os.path.exists("assets"):
        files_in_assets = [f for f in listdir("assets") if isfile(join("assets", f))]
    app_file = None
    logo_file = None
    for fn in files_in_assets:
        fn_without_extension, _, extension = fn.partition(".")
        if extension.lower() in valid_extensions:
            if (
                fn_without_extension == page_id
                or fn_without_extension == page_id.replace("_", "-")
            ):
                return fn

            if fn_without_extension == "app":
                app_file = fn

            if fn_without_extension == "logo":
                logo_file = fn

    if app_file:
        return app_file

    return logo_file


def _filename_to_name(filename):
    return filename.split(".")[-1].replace("_", " ").capitalize()


def _validate_template(template):
    template_segments = template.split("/")
    for s in template_segments:
        if "<" in s or ">" in s:
            if not (s.startswith("<") and s.endswith(">")):
                raise Exception(
                    f'Invalid `path_template`: "{template}"  Path segments with variables must be formatted as <variable_name>'
                )
            variable_name = s[1:-1]
            if not variable_name.isidentifier() or iskeyword(variable_name):
                warnings.warn(
                    f'`{variable_name}` is not a valid Python variable name in `path_template`: "{template}".',
                    stacklevel=2,
                )
    return template


def _infer_path(filename, template):
    if template is None:
        path = filename.replace("_", "-").replace(".", "/").lower().split("pages")[-1]
        path = "/" + path if not path.startswith("/") else path
        return path
    else:
        # replace the variables in the template with "none" to create a default path if no path is supplied
        path_segments = template.split("/")
        default_template_path = [
            "none" if s.startswith("<") else s for s in path_segments
        ]
        return "/".join(default_template_path)


def _parse_query_string(search):
    if search and len(search) > 0 and search[0] == "?":
        search = search[1:]
    else:
        return {}

    parsed_qs = {}
    for (k, v) in parse_qs(search).items():
        v = v[0] if len(v) == 1 else v
        parsed_qs[k] = v
    return parsed_qs


def _parse_path_variables(pathname, path_template):
    """
    creates the dict of path variables passed to the layout
    e.g. path_template= "/asset/<asset_id>"
         if pathname provided by the browser is "/assets/a100"
         returns **{"asset_id": "a100"}
    """
    path_segments = pathname.split("/")
    template_segments = path_template.split("/")

    if len(path_segments) != len(template_segments):
        return None

    path_vars = {}
    for path_segment, template_segment in zip(path_segments, template_segments):
        if template_segment.startswith("<"):
            path_vars[template_segment[1:-1]] = path_segment
        elif template_segment != path_segment:
            return None
    return path_vars


def register_page(
    module,
    path=None,
    path_template=None,
    name=None,
    order=None,
    title=None,
    description=None,
    image=None,
    redirect_from=None,
    layout=None,
    **kwargs,
):
    """ """
    return app_register_page(
        PAGE_REGISTRY,
        module,
        path,
        path_template,
        name,
        order,
        title,
        description,
        image,
        redirect_from,
        layout,
        **kwargs,
    )


def app_register_page(
    page_registry,
    module,
    path=None,
    path_template=None,
    name=None,
    order=None,
    title=None,
    description=None,
    image=None,
    redirect_from=None,
    layout=None,
    **kwargs,
):
    # COERCE
    # - Set the order
    # - Inferred paths
    page = dict(
        module=module,
        supplied_path=path,
        path_template=None
        if path_template is None
        else _validate_template(path_template),
        path=(path if path is not None else _infer_path(module, path_template)),
        supplied_name=name,
        name=(name if name is not None else _filename_to_name(module)),
    )
    page.update(
        supplied_title=title,
        title=(title if title is not None else page["name"]),
    )
    page.update(
        description=description if description else "",
        order=order,
        supplied_order=order,
        supplied_layout=layout,
        **kwargs,
    )
    page.update(
        image=(image if image is not None else _infer_image(module)),
        supplied_image=image,
    )
    page.update(redirect_from=redirect_from)

    page_registry[module] = page

    if layout is not None:
        # Override the layout found in the file set during `plug`
        page_registry[module]["layout"] = layout

    # set home page order
    order_supplied = any(
        p["supplied_order"] is not None for p in page_registry.values()
    )

    for p in page_registry.values():
        p["order"] = (
            0 if p["path"] == "/" and not order_supplied else p["supplied_order"]
        )

    # sorted by order then by module name
    page_registry_list = sorted(
        page_registry.values(),
        key=lambda i: (str(i.get("order", i["module"])), i["module"]),
    )

    page_registry = collections.OrderedDict(
        [(p["module"], p) for p in page_registry_list]
    )

    global PAGE_REGISTRY
    PAGE_REGISTRY = page_registry
