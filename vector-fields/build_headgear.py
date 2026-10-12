"""Compile the detailed optional helmets using the existing fitted head bone."""
import argparse
from headgear_geometry import OUT, ROOT, build

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ensure', action='store_true')
    build(parser.parse_args().ensure)
