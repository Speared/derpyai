"""Get login info from environment."""

# Import built-in modules
import os


def get_login():
    """Get login info from environment.

    Returns:
        dict: Login info.

    """
    return {
        'server': os.environ.get("DERPY_SERVER",
                                 "https://crawl.kelbi.org/#lobby"),
        'username': os.environ.get("DERPY_USERNAME", "username"),
        'password': os.environ.get("DERPY_PASSWORD", "password"),
    }
