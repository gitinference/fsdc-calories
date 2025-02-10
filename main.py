from src.data_process import DataCal


def main() -> None:
    print(DataCal().process_int_org(agg="monthly", types="hts").execute())


if __name__ == "__main__":
    main()
