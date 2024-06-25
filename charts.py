import json

import matplotlib.pyplot as plt


def update_plate_charts():
    with open('nutrition_data/nutrient_distribution_yearly.json', 'r') as fp:
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

        plt.savefig(f"plate_graphs/{year}.png")
        plt.close()


if __name__ == '__main__':
    update_plate_charts()
