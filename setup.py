#!/usr/bin/env python3
"""Gmail Monitor setup wizard with ASCII art banner."""

import os
import random
import sys

BANNER = r"""
  ██████╗ ███╗   ███╗ █████╗ ██╗██╗
 ██╔════╝ ████╗ ████║██╔══██╗██║██║
 ██║  ███╗██╔████╔██║███████║██║██║
 ██║   ██║██║╚██╔╝██║██╔══██║██║██║
 ╚██████╔╝██║ ╚═╝ ██║██║  ██║██║███████╗
  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝
 ███╗   ███╗ ██████╗ ███╗   ██╗██╗████████╗ ██████╗ ██████╗
 ████╗ ████║██╔═══██╗████╗  ██║██║╚══██╔══╝██╔═══██╗██╔══██╗
 ██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║   ██║   ██║██████╔╝
 ██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║██╔══██╗
 ██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝██║  ██║
 ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
"""

PALETTES = [
    ["\033[34m", "\033[35m", "\033[94m", "\033[95m", "\033[96m"],
    ["\033[31m", "\033[91m", "\033[33m", "\033[93m", "\033[31m"],
    ["\033[32m", "\033[92m", "\033[36m", "\033[96m", "\033[32m"],
    ["\033[33m", "\033[93m", "\033[91m", "\033[31m", "\033[33m"],
    ["\033[35m", "\033[95m", "\033[34m", "\033[94m", "\033[35m"],
    ["\033[36m", "\033[96m", "\033[92m", "\033[32m", "\033[36m"],
    ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m"],
]

RESET = "\033[0m"


def render_banner():
    palette = random.choice(PALETTES)
    for i, line in enumerate(BANNER.strip().split("\n")):
        color = palette[i % len(palette)]
        print(f"{color}{line}{RESET}")
    print()
    print("  Gmail Monitor v1.0.0")
    print("  Automated job search and legal update monitoring")
    print()


def ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    answer = input(f"  {prompt}{suffix}: ").strip()
    return answer or default


def main():
    render_banner()

    print("  Let's set up your Gmail Monitor.\n")
    print("  You'll need a Gmail App Password (not your account password).")
    print("  Get one at: https://myaccount.google.com/apppasswords\n")

    gmail_user = ask("Gmail address")
    gmail_password = ask("Gmail App Password")
    output_dir = ask("Output directory", "/data/gmail-monitor")
    summary_file = ask("Summary file path", "/data/.claude/monitor-summary.md")
    timezone = ask("Timezone", "America/Los_Angeles")

    env_content = (
        f"GMAIL_USER={gmail_user}\n"
        f"GMAIL_APP_PASSWORD={gmail_password}\n"
        f"OUTPUT_DIR={output_dir}\n"
        f"SUMMARY_FILE={summary_file}\n"
        f"TZ={timezone}\n"
    )

    env_path = os.path.join(os.getcwd(), ".env")
    with open(env_path, "w") as f:
        f.write(env_content)

    print(f"\n  \033[32m+\033[0m Configuration saved to {env_path}")
    print()
    print("  Next steps:")
    print("    1. docker build -t gmail-monitor:latest .")
    print("    2. docker run -d --name gmail-monitor --env-file .env \\")
    print(f"         -v /path/to/gmail-monitor:{output_dir}:rw \\")
    print("         -v /path/to/.claude:/data/.claude:rw \\")
    print("         gmail-monitor:latest")
    print()
    print("  Or run locally: python src/scheduler.py")
    print()


if __name__ == "__main__":
    main()
