from jinja2 import Environment, select_autoescape, PackageLoader


def filter_if_exists(
    value: str | None,
    pattern: str = "{}",
) -> str:
    """
    If value is None, returns empty string.
    Otherwise replaces '{}' in the pattern with the value.
    Examples:
    - value="hello", pattern="#prefix {}" -> "#prefix hello"
    - value="hello", pattern="{}"         -> "hello"
    - value="hello", pattern="test=[{}]"  -> "test=[hello]"
    - value=None                          -> ""

    """
    if value is None:
        return ""

    if "{}" not in pattern:
        return f"{pattern}{value}"

    return pattern.format(value)


def filter_if_true(
    text: str,
    condition: bool,
) -> str:
    """
    Returns text if condition is True, else returns empty string.
    In default jinja you need to always add else
    """
    return text if condition else ""


def filter_if_true_with_pattern(
    text: str,
    condition: bool,
    pattern: str = "{}",
) -> str:
    """
    If condition is True, returns pattern with value inserted.
    Otherwise returns empty string.
    Examples:
    - value="hello", condition=True, pattern="#prefix {}" -> "#prefix hello"
    - value="hello", condition=True, pattern="{}"         -> "hello"
    - value="hello", condition=True, pattern="test=[{}]" -> "test=[hello]"
    - condition=False                                     -> ""

    """
    if not condition:
        return ""

    if "{}" not in pattern:
        return f"{pattern}{text}"

    return pattern.format(text)


class TemplateManager:
    _env = None
    DEBUG = False
    MODULE_NAME: str | None = ""

    @classmethod
    def set_debug(cls, debug: bool):
        cls.DEBUG = debug

    @classmethod
    def set_module_name(cls, module_name: str):
        cls.MODULE_NAME = module_name

    @classmethod
    def get_env(cls, debug: bool = False) -> Environment:
        if cls._env is None:
            package_name = __name__.split(".")[0]
            cls._env = Environment(
                loader=PackageLoader(package_name, "templates"),
                autoescape=select_autoescape(),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True,
            )
            # add here filters
            cls._env.filters["if_exists"] = filter_if_exists
            cls._env.filters["if_true"] = filter_if_true_with_pattern
        return cls._env

    @classmethod
    def render_master(cls, template_name: str, **kwargs) -> str:
        """
        Renders a template by name.
        """
        if cls.MODULE_NAME is None:
            raise ValueError(
                "MODULE_NAME is not set in TemplateManager. "
                "Please set it before rendering templates: "
                "TemplateManager.set_module_name(...)"
            )
        env = cls.get_env()
        template = env.get_template(template_name)
        kwargs["debug"] = cls.DEBUG
        kwargs["module_name"] = cls.MODULE_NAME
        return template.render(**kwargs).strip()

    @classmethod
    def render_component(cls, template_str: str, **kwargs) -> str:
        """
        Renders a template component from a string.
        """
        if cls.MODULE_NAME is None:
            raise ValueError(
                "MODULE_NAME is not set in TemplateManager. "
                "Please set it before rendering templates: "
                "TemplateManager.set_module_name(...)"
            )
        env = cls.get_env()
        template = env.from_string(template_str)
        kwargs["debug"] = cls.DEBUG
        kwargs["module_name"] = cls.MODULE_NAME
        return template.render(**kwargs).strip()
