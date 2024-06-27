import json

import matplotlib.pyplot as plt


def main():
    pass


def update_plate_charts():
    print("Generating MyPlate charts")

    with open('data/plate/nutrient_distribution_yearly.json', 'r') as fp:
        nutrient_distribution_data: dict = json.load(fp)

    for year in nutrient_distribution_data:
        current_year_data = nutrient_distribution_data[year]

        # Create a pie chart
        fig, ax = plt.subplots()
        ax.pie(current_year_data.values(), autopct='%1.1f%%', startangle=90)

        # Equal aspect ratio ensures that pie is drawn as a circle.
        ax.axis('equal')

        # Title of the pie chart
        plt.title(f"Nutrient Distribution for {year}")

        plt.legend(current_year_data.keys(), loc='upper left', bbox_to_anchor=(-0.15, 1.12), borderaxespad=0.)

        plt.savefig(f"charts/plate/{year}.png")
        plt.close()

    print(f"Done, can be found at charts/plate/<year>.png)")


def update_timeseries_charts():
    pass


def generate_custom_timeseries_chart(start_year, end_year, macronutrient):
    pass


if __name__ == '__main__':
    main()
