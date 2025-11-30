"""
Utility to close all open ERC3 sessions.

Usage:
    python close_sessions.py          # dry run - show what would be closed
    python close_sessions.py --force  # actually close sessions
"""

import argparse
from dotenv import load_dotenv
from erc3 import ERC3

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Close all open ERC3 sessions")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Actually close sessions (without this flag, only shows what would be closed)",
    )
    args = parser.parse_args()

    core = ERC3()

    sessions = core.search_sessions()

    open_sessions = [s for s in sessions.sessions if s.status == "open"]

    if not open_sessions:
        print("No open sessions found.")
        return

    print(f"Found {len(open_sessions)} open session(s)\n")

    for session in open_sessions:
        print("=" * 60)
        print(f"Session: {session.id}")
        print(f"  Benchmark: {session.benchmark_type}")
        print(f"  Created: {session.created_at}")
        print(
            f"  Tasks: {session.total_tasks} total, {session.new_tasks} new, {session.running_tasks} running,"
            f"{session.completed_tasks} completed"
        )

        if not args.force:
            print("  [DRY RUN] Would close this session")
            continue

        # Get session status to access tasks
        status = core.session_status(session.id)

        # Close uncompleted tasks
        unclosed_tasks = [t for t in status.tasks if t.status != "completed"]

        for task in unclosed_tasks:
            print(f"  Closing task: {task.task_id} (status: {task.status})")
            try:
                # Start task if it's new
                if task.status == "new":
                    core.start_task(task)
                # Complete the task
                core.complete_task(task)
            except Exception as e:
                print(f"    Error closing task: {e}")

        # Submit session
        try:
            core.submit_session(session.id)
            print(f"  Session {session.id} closed")
        except Exception as e:
            print(f"  Error closing session: {e}")

    print("\n" + "=" * 60)
    if args.force:
        print(f"Done. Closed {len(open_sessions)} session(s).")
    else:
        print(
            f"Dry run complete. Use --force to actually close {len(open_sessions)} session(s)."
        )


if __name__ == "__main__":
    main()
