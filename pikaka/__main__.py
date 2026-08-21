"""Entrypoints — installed as the `pikaka` command (and `python -m pikaka`):

  pikaka                       chat in the terminal (default)
  pikaka dashboard             the browser cockpit → localhost:7777 (+ Telegram if configured)
  pikaka connections           list configured integrations and their health
  pikaka voice                 talk to it (needs the [voice] extra)
  pikaka telegram              phone → laptop (needs TELEGRAM_BOT_TOKEN)
  pikaka discord               Discord → laptop (needs DISCORD_BOT_TOKEN)
  pikaka whatsapp              WhatsApp → laptop (needs WHATSAPP_TOKEN, public URL)
  pikaka brief                 morning briefing (calendar + mail + memory) — as a LOOP
  pikaka gather                same job as a GRAPH: github, web, calendar and
                             memory fetched together, then one digest
  pikaka skill install <url>   install a community skill
"""

from __future__ import annotations

import sys


def main() -> None:
    args = sys.argv[1:]
    if not args:
        from pikaka.gateway.cli import main as cli_main

        cli_main()
    elif args[0] == "dashboard":
        from pikaka.ops.dashboard import main as dash_main

        dash_main()
    elif args[0] == "connections":
        from pikaka.integrations import cli_main

        sys.exit(cli_main())
    elif args[0] == "voice":
        from pikaka.gateway.voice import main as voice_main

        voice_main()
    elif args[0] == "telegram":
        from pikaka.gateway.telegram import main as tg_main

        tg_main()
    elif args[0] == "discord":
        from pikaka.gateway.discord import main as discord_main

        discord_main()
    elif args[0] == "whatsapp":
        from pikaka.gateway.whatsapp import main as wa_main

        wa_main()
    elif args[0] == "brief":
        from pikaka.ops.brief import main as brief_main

        brief_main()
    elif args[0] == "gather":
        from pikaka.ops.gather import main as gather_main

        gather_main()
    elif args[0] == "skill" and len(args) >= 3 and args[1] == "install":
        from pikaka.memory.procedural.installer import install

        install(args[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
