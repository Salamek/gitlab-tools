# -*- coding: utf-8 -*-


def main():
    """Entrypoint to the ``celery`` umbrella command."""
    from gitlab_tools.bin.gitlab_tools import main as _main
    _main()


if __name__ == '__main__':  # pragma: no cover
    main()
