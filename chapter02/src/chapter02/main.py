#!/usr/bin/env python3
"""
Winston Kernel - Chapter 2 Implementation Selector
Entry point for demonstrating different stages of Winston's development.
"""

from typing import Callable


def run_basic_kernel() -> None:
    """Run the basic three-function cognitive kernel."""
    from . import basic_kernel

    basic_kernel.main()


def run_minimal_kernel() -> None:
    """Run the complete Winston kernel with intent-based actions."""
    from . import minimal_kernel

    minimal_kernel.main()


def main() -> None:
    """Interactive menu for selecting which Winston implementation to run."""
    print("Winston Kernel - Chapter 2 Implementations")
    print("==========================================")
    print()
    print("Choose which implementation to run:")
    print("1. Basic Kernel (Three-function paradigm + action trace)")
    print("2. Minimal Kernel (Complete Winston with semantic matching)")
    print("q. Quit")
    print()

    implementations: dict[str, Callable[[], None]] = {
        "1": run_basic_kernel,
        "2": run_minimal_kernel,
    }

    while True:
        try:
            choice = input("Selection [1/2/q]: ").strip().lower()

            if choice in ["q", "quit", "exit"]:
                print("Goodbye!")
                break
            elif choice in implementations:
                print(f"\nStarting implementation {choice}...")
                print("-" * 40)
                implementations[choice]()
                print("\nReturning to main menu...")
                print("=" * 40)
                print()
            else:
                print("Invalid choice. Please enter 1, 2, or q.")
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
