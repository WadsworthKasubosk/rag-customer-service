import argparse

from app.store.seed import init_demo_data


def main():
    parser = argparse.ArgumentParser(description="Initialize MySQL schema and demo data.")
    parser.add_argument("--reset", action="store_true", help="Reset repair, logistics, chat, and feedback demo data.")
    args = parser.parse_args()

    result = init_demo_data(reset_runtime=args.reset)
    print(
        "[init_db] MySQL schema ready: "
        f"{result['repair_tickets']} repair tickets, "
        f"{result['logistics_orders']} logistics orders"
    )


if __name__ == "__main__":
    main()
