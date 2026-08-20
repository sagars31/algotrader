import csv
import glob
import pandas as pd

# Read all CSV files in the current directory one by one
# df_list = []
# for file in glob.glob("data/sectors/*.csv"):
#     df = pd.read_csv(file)
#     df["Source_File"] = file.split("/")[-1]  # optional: track which file each row came from
#     df_list.append(df)


for file in glob.glob("data/sectors/*.csv"):
    df = pd.read_csv(file)
    print(df.columns.tolist())
    df.rename(columns={
        'Stock Name': 'Stock_Name',
        'Market Cap(Rs. Cr.)': 'Market_Cap_Cr'
        }, inplace=True)
    print(df.columns.tolist())
    df = df.sort_values(by="Market_Cap_Cr", ascending=False)
    df['Rank'] = range(1, len(df) + 1)
    df[["Rank","Stock_Name", "Symbol", "Sector", "Industry", "Market_Cap_Cr"]].to_csv(file, index=False)

# # Combine all DataFrames into one
# combined_df = pd.concat(df_list, ignore_index=True)
# combined_df = combined_df.sort_values(by="Market Cap(Rs. Cr.)", ascending=False)

# # Save the combined data to a single CSV
# combined_df.to_csv("data/nse_equity.csv", index=False)



        # first_line = next(reader, None)
        # sector = first_line[0].replace("ï»¿Sector: ", "").strip()
        # print(sector)
        # df = pd.read_csv(filename, skiprows=5)
        # df = df.dropna(how="all").reset_index(drop=True)
        # df["Sector"] = sector
        # print(df.head())
        # filenameupdated = filename.replace(" ", "_").replace("-", "").replace("&", "").lower()
        # # filepath = "data/sector_updated/" + filenameupdated + ".csv"
        # # print("Saving updated CSV to:", filepath)
        # # df = df.rename(columns={
        # #     "Stock Name": "Stock_Name",
        # #     "Market Cap(Rs. Cr.)": "Market_Cap_Cr"
        # # }, inplace=True)
        # df[["Stock Name", "Symbol", "Sector", "Industry", "Market Cap(Rs. Cr.)"]].to_csv(filename, index=False)