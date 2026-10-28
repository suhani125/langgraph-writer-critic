import argparse

from dotenv import load_dotenv

load_dotenv()

from src.graph import build_graph  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="LangGraph Writer-Critic demo")
    parser.add_argument("topic", nargs="?", default="why the sky is blue")
    parser.add_argument("--diagram", action="store_true", help="print Mermaid diagram")
    args = parser.parse_args()

    app = build_graph()

    if args.diagram:
        print(app.get_graph().draw_mermaid())
        return

    state = {"topic": args.topic, "draft": "", "feedback": "", "approved": False, "revisions": 0}
    final = state
    for step in app.stream(state, stream_mode="updates"):
        for node, update in step.items():
            print(f"\n=== {node.upper()} ===")
            print(update.get("draft") or update.get("feedback"))
            final = {**final, **update}

    status = "approved" if final["approved"] else "max revisions reached"
    print(f"\n✅ Done after {final['revisions']} draft(s) ({status}).")


if __name__ == "__main__":
    main()
