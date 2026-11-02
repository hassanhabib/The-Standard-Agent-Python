# ---------------------------------------------------------------
# Copyright (c) Hassan Habib All rights reserved.
# Licensed under the The Standard Software License (TSSL)
# ---------------------------------------------------------------

"""python -m standard_agents.host: the agent definition, served over HTTP."""

from standard_agents.host.program import main

# Guarded, because anything that walks the package (the architecture tests do) imports this
# module too, and importing it must not start a server.
if __name__ == "__main__":
    raise SystemExit(main())
