import os
from os import listdir
from os.path import isfile, join
import collections
from urllib.parse import parse_qs
from . import _validate


PAGE_REGISTRY = collections.OrderedDict()


def get_page_registry():
    page_registry_list = sorted(
        PAGE_REGISTRY.values(),
        key=lambda i: (str(i.get("order", i["module"])), i["module"]),
    )
    return collections.OrderedDict([(p["module"], p) for p in page_registry_list])


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
    # todo need to check for other assets folders?

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
    """
    Assigns the variables to `dash.page_registry` as an `OrderedDict`
    (ordered by `order`).

    `dash.page_registry` is used by `pages_plugin` to set up the layouts as
    a multi-page Dash app. This includes the URL routing callbacks
    (using `dcc.Location`) and the HTML templates to include title,
    meta description, and the meta description image.

    `dash.page_registry` can also be used by Dash developers to create the
    page navigation links or by template authors.

    - `module`:
       The module path where this page's `layout` is defined. Often `__name__`.

    - `path`:
       URL Path, e.g. `/` or `/home-page`.
       If not supplied, will be inferred from the `path_template` or `module`,
       e.g. based on path_template: `/asset/<asset_id` to `/asset/none`
       e.g. based on module: `pages.weekly_analytics` to `/weekly-analytics`

    - `path_template`:
       Add variables to a URL by marking sections with <variable_name>. The layout function
       then receives the <variable_name> as a keyword argument.
       e.g. path_template= "/asset/<asset_id>"
            then if pathname in browser is "/assets/a100" then layout will receive **{"asset_id":"a100"}

    - `name`:
       The name of the link.
       If not supplied, will be inferred from `module`,
       e.g. `pages.weekly_analytics` to `Weekly analytics`

    - `order`:
       The order of the pages in `page_registry`.
       If not supplied, then the filename is used and the page with path `/` has
       order `0`

    - `title`:
       (string or function) The name of the page <title>. That is, what appears in the browser title.
       If not supplied, will use the supplied `name` or will be inferred by module,
       e.g. `pages.weekly_analytics` to `Weekly analytics`

    - `description`:
       (string or function) The <meta type="description"></meta>.
       If not supplied, then nothing is supplied.

    - `image`:
       The meta description image used by social media platforms.
       If not supplied, then it looks for the following images in `assets/`:
        - A page specific image: `assets/<title>.<extension>` is used, e.g. `assets/weekly_analytics.png`
        - A generic app image at `assets/app.<extension>`
        - A logo at `assets/logo.<extension>`
        When inferring the image file, it will look for the following extensions: APNG, AVIF, GIF, JPEG, PNG, SVG, WebP.

    - `redirect_from`:
       A list of paths that should redirect to this page.
       For example: `redirect_from=['/v2', '/v3']`

    - `layout`:
       The layout function or component for this page.
       If not supplied, then looks for `layout` from within the supplied `module`.

    - `**kwargs`:
       Arbitrary keyword arguments that can be stored

    ***

    `page_registry` stores the original property that was passed in under
    `supplied_<property>` and the coerced property under `<property>`.
    For example, if this was called:
    ```
    register_page(
        'pages.historical_outlook',
        name='Our historical view',
        custom_key='custom value'
    )
    ```
    Then this will appear in `page_registry`:
    ```
    OrderedDict([
        (
            'pages.historical_outlook',
            dict(
                module='pages.historical_outlook',

                supplied_path=None,
                path='/historical-outlook',

                supplied_name='Our historical view',
                name='Our historical view',

                supplied_title=None,
                title='Our historical view'

                supplied_layout=None,
                layout=<function pages.historical_outlook.layout>,

                custom_key='custom value'
            )
        ),
    ])
    ```
    """
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
        else _validate.validate_template(path_template),
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
