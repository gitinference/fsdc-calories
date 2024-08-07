import pandas as pd
import urllib.request
from tempfile import TemporaryFile
import ssl
import chardet
import matplotlib.pyplot as plt
import numpy as np


ssl._create_default_https_context = ssl._create_unverified_context


def main():
    fetch_energy_data()


def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        detector = chardet.universaldetector.UniversalDetector()
        for line in file:
            detector.feed(line)
            if detector.done:
                break
        detector.close()
    return detector.result['encoding']


def fetch_energy_data():
    # Fetch energy indicators from LUMA dataset
    url = ('https://indicadores.pr/dataset/49746389-12ce-48f6-b578-65f6dc46f53f/resource/8025f821-45c1-4c6a-b2f4'
           '-8d641cc03df1/download/aee-meta-ultimo.csv')

    f, res = urllib.request.urlretrieve(url)
    encoding = detect_encoding(f)

    # Read CSV into dataframe
    df = pd.read_csv(url, encoding=encoding)
    df = df.drop('Comentarios', axis=1)

    def parse_date(row: pd.Series):
        val = row.split('/')
        val = [num.zfill(2) for num in val]  # Add left zeros up to 2 characters

        # Convert from MM/DD/YYYY to YYYY/MM/DD
        val[0], val[1], val[2] = val[2], val[0], val[1]
        val = "-".join(val)
        return val

    df["Mes"] = df["Mes"].map(parse_date)
    df["Mes"] = pd.to_datetime(df["Mes"])

    df.rename(columns={"Mes": "Date"}, inplace=True)

    # Clean column names to remove random spaces with rstrip and lstrip
    df.rename(columns={
        colname: colname.rstrip().lstrip() for colname in df.columns.values
    }, inplace=True)

    # Clean values in each column to allow float casting
    def clean_value(val: any):
        val = str(val)
        val = val.replace(",", "")

        try:
            val = float(val)
        except ValueError:
            val = np.nan

        return val

    for colname in df.columns[1:]:
        df[colname] = df[colname].map(clean_value)

    return df


if __name__ == '__main__':
    main()
