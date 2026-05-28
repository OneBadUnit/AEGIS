# ==========================================
# SWAT SIGNAL DESK
# File: collector_runner.py
# Phase: 1A (Rename + Reframe)
# Version: 002
# ==========================================

from tasks.run_collectors import run_all_collectors


def main():
    print("")
    print("===================================")
    print(" SWAT SIGNAL DESK — COLLECTOR")
    print("===================================")
    print("")

    summary = run_all_collectors()

    print("")
    print("===================================")
    print(" RUN COMPLETE")
    print("===================================")
    print("")
    print(summary)


if __name__ == "__main__":
    main()