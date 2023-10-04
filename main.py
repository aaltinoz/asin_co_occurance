import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

from google.colab import files


def get_cooccurances():
  STORE_NAME = input('Please enter Store Name: ')
  print("Please upload Transaction data as a csv file")
  transaction_data = files.upload()
  #Get Transaction data
  filename = list(transaction_data.keys())[0]
  transaction_data = pd.read_csv(filename,skiprows = 7,usecols=['date/time','type','order id', 'sku'])

  # Get the dates
  START_DATE = pd.to_datetime(transaction_data['date/time']).dt.date.min().strftime('%m-%Y')
  END_DATE = pd.to_datetime(transaction_data['date/time']).dt.date.max().strftime('%m-%Y')

  #Get ASIN data
  print('Please upload Eva Pricing Report')

  eva_pricing_report = files.upload()

  filename = list(eva_pricing_report.keys())[0]
  eva_pricing_report = pd.read_csv(filename)

  # filter and drop NaN values
  transaction_data = transaction_data.rename(columns={'sku':'SKU'})
  transaction_data = transaction_data[transaction_data["type"] == "Order"].dropna()

  # Merge ASIN's to corresponding SKU's from eva_pricing_report
  transaction_data = transaction_data.merge(eva_pricing_report[['SKU','ASIN']], on = 'SKU', how = 'left')

  # Create asin_cf file
  asin_cf = transaction_data[['order id','ASIN']].copy()
  asin_cf["order id"] = asin_cf.loc[:,"order id"].astype("category")
  asin_cf["ASIN"] = asin_cf.loc[:,"ASIN"].astype("category")

  # Convert to one-hot encoded format
  oht_df = pd.get_dummies(asin_cf.set_index('order id')['ASIN']).reset_index()
  oht_df_grouped = oht_df.groupby('order id').sum()

  # Calculate co-occurrence
  co_occurrence = oht_df_grouped.T.dot(oht_df_grouped)

  # Set the diagonal to zero as it represents the SKU with itself
  for asin in co_occurrence.columns:
      co_occurrence.loc[asin, asin] = 0

  # Filter rows and columns where all values are zero
  co_occurrence = co_occurrence.loc[(co_occurrence != 0).any(axis=1), (co_occurrence != 0).any(axis=0)]

  # Extract pairs where co-occurrence is greater than 0
  non_zero_pairs = co_occurrence.stack().reset_index()
  non_zero_pairs.columns = ['ASIN_1', 'ASIN_2', 'Co-occurrence']
  non_zero_pairs = non_zero_pairs[non_zero_pairs['Co-occurrence'] > 0]

  # Filter to top N co-occurrences
  N = 20
  top_pairs = non_zero_pairs.nlargest(N, 'Co-occurrence')

  # Create a pivot for the heatmap
  heatmap_data = top_pairs.pivot('ASIN_1', 'ASIN_2', 'Co-occurrence')
  heatmap_data = heatmap_data.fillna(0)

    # Sort the ASINs in each row
  non_zero_pairs[['min_ASIN', 'max_ASIN']] = non_zero_pairs[['ASIN_1', 'ASIN_2']].apply(lambda row: sorted(row), axis=1, result_type='expand')

  # Drop duplicates based on sorted ASINs
  non_zero_pairs = non_zero_pairs.drop_duplicates(subset=['min_ASIN', 'max_ASIN'])

  # Drop temporary columns
  non_zero_pairs = non_zero_pairs.drop(columns=['min_ASIN', 'max_ASIN'])

  # Write it to excel
  non_zero_pairs.sort_values(by="Co-occurrence",ascending=False).to_excel(f"{STORE_NAME.replace(' ','_')}_ASIN_Cooccurance_between_{START_DATE}_{END_DATE}.xlsx", index=False)

  # Draw the heatmap
  plt.figure(figsize=(10, 8))
  sns.heatmap(heatmap_data, annot=True, cmap='Blues')
  plt.title(f"Top {N} SKU Co-occurrences for {STORE_NAME} between {START_DATE} - {END_DATE}")
  plt.show()
  return None
