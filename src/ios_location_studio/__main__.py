"""Allow ``python -m ios_location_studio``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
