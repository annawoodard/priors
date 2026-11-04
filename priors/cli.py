"""priors: keep a literature library that agents maintain and you question.

Commands:
  priors init <dir> --owner NAME --domain "field"   create a library
  priors index [--check]                            rebuild index.md and check the tree
  priors lookup <command> ...                       query OpenAlex and arXiv (see: priors lookup -h)
  priors where                                      print the library and engine paths

Commands other than init run on the library found from the current folder,
or on $PRIORS_LIBRARY if set.
"""

import sys

from . import ENGINE


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return
    command, rest = argv[0], argv[1:]
    if command == "init":
        from . import init

        init.main(rest)
    elif command == "index":
        from . import index

        index.main(rest)
    elif command == "lookup":
        from . import lookup

        lookup.main(rest)
    elif command == "where":
        from . import config

        root = config.find_library()
        print(f"library: {root}\nengine:  {ENGINE}\nprocedures: {ENGINE / 'procedures'}")
    else:
        sys.exit(f"unknown command {command!r}; run `priors -h`")


if __name__ == "__main__":
    main()
