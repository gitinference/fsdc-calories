from fsdc_calories import DataCal


def main():
    DataCal().process_int_jp(time_frame="monthly", level="hts")


if __name__ == "__main__":
    main()
