import json

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import io


def main():
    pass


def update_plate_charts():
    print("Generating MyPlate charts")

    with open('data/plate/nutrient_distribution_yearly.json', 'r') as fp:
        nutrient_distribution_data: dict = json.load(fp)

    latest_month = nutrient_distribution_data["latest_year_extra"]["latest_month"]
    nutrient_distribution_data.pop("latest_year_extra")

    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December"]

    for year in nutrient_distribution_data:
        current_year_data = nutrient_distribution_data[year]

        # Create a pie chart
        fig, ax = plt.subplots()
        ax.pie(current_year_data.values(), autopct='%1.1f%%', startangle=90)

        # Equal aspect ratio ensures that pie is drawn as a circle.
        ax.axis('equal')

        # Title of the pie chart
        title = f"Nutrient Distribution for {year}"
        if year == max(nutrient_distribution_data):
            # Pop latest month from JSON data
            title += f" (as of {months[latest_month - 1]})"

        plt.title(title)
        plt.legend(current_year_data.keys(), loc='upper left', bbox_to_anchor=(-0.15, 1.12), borderaxespad=0.)

        plt.savefig(f"charts/plate/{year}.png")
        plt.close()

    print(f"Done, can be found at charts/plate/<year>.png)")


def generate_timeseries_chart(tseries_start, tseries_end, macronutrient):
    with open('data/macronutrients/hts_macronutrients_data.csv', 'r') as f:
        df = pd.read_csv(f)

    fig, ax = plt.subplots()

    data = {}
    for year in range(tseries_start, tseries_end + 1):
        yearly = df[df["year"] == year]
        start, end = 1, 3
        trimester = 1
        while trimester <= 4:
            trimester_sum = yearly[(yearly["month"] >= start) & (yearly["month"] <= end)][macronutrient].sum()
            data[f"{year % 100}-T{trimester}"] = trimester_sum
            start += 3
            end += 3
            trimester += 1

    x_axis = list(data.keys())
    y_axis = [x / 1_000_000 for x in data.values()]
    for y in data:
        print(y, data[y])
    try:
        assert len(x_axis) == len(y_axis)
    except AssertionError:
        print("Length of x_axis and y_axis do not match")

    ax.plot(x_axis, y_axis, '--bo')
    x_ticks = x_axis[1::2] if tseries_end - tseries_start > 3 else x_axis
    ax.set_xticks(x_ticks)
    ax.get_yaxis().set_major_formatter(ticker.FuncFormatter(lambda x, p: format(int(x), ',')))

    plt.ylabel(f"{macronutrient} (in millions)")
    plt.xlabel("timeperiod (YY-T<trimester>)")
    plt.title(f"{macronutrient} from {tseries_start} to {tseries_end}")

    def set_size(w, h):
        """ w, h: width, height in inches """
        ax = plt.gca()
        left = ax.figure.subplotpars.left
        right = ax.figure.subplotpars.right
        top = ax.figure.subplotpars.top
        bottom = ax.figure.subplotpars.bottom
        figw = float(w) / (right - left)
        figh = float(h) / (top - bottom)
        ax.figure.set_size_inches(figw, figh)

    set_size(10, 6)
    f = io.BytesIO()
    plt.savefig(f, format='png')

    return f


if __name__ == '__main__':
    main()
