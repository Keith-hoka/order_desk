"""Run the eval-regression gate; exit 1 on regression (Phase 10, for CI).

Reads the committed eval reports named in the adapter registry and checks the
candidate adapter has not regressed headline F1 beyond tolerance on any frozen
eval source. Prints a table and exits non-zero if the gate fails, so CI blocks
a change that ships a regressed adapter.
"""

import sys

from order_desk.flywheel.regression import check_regression, format_report


def main() -> None:
    gate = check_regression()
    print(format_report(gate))
    if not gate.passed:
        print("\nRegression gate FAILED -- a candidate adapter dropped F1 beyond tolerance.")
        sys.exit(1)
    print("\nRegression gate passed.")


if __name__ == "__main__":
    main()
