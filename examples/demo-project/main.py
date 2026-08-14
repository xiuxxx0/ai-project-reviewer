"""Demo CLI 入口。"""
import sys

from utils import greet


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "world"
    print(greet(name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
