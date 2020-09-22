import os
import pandas

import country_converter

from tools import calculate_data_freshness_per_country
from tools import generate_full_data
from tools import jhu_global_data

# The directories (inside app/) where JSON files for country-specific and
# day-specific data are expected to reside.
COUNTRIES_DIR = "app/countries"
DAILIES_DIR = "app/dailies"

self_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")

def build_case_count_table_from_line_list(in_data):
    """
    This takes an input data frame where each row represents a single
    case, with a confirmation date and a geo ID, and returns a data
    frame where each row represents a single date, columns are unique
    geo IDs and cells are the sum of corresponding case counts.
    """
    unique_dates = in_data.date.unique()
    unique_geoids = in_data.geoid.unique()
    unique_geoids.sort()
    out_data = pandas.DataFrame(columns=unique_geoids, index=unique_dates)

    out_data.index.name = "date"
    for date in out_data.index:
        out_data.loc[date] = in_data[in_data.date == date].geoid.value_counts()
    out_data = out_data.fillna(0)
    out_data.reset_index(drop=False)
    return out_data

# Returns whether we were able to get the necessary data
def retrieve_generable_data(out_dir, should_overwrite=False, quiet=False):
    from tools import scrape_total_count

    success = True
    out_path = os.path.join(out_dir, "globals.json")
    if not os.path.exists(out_path) or should_overwrite:
        success &= scrape_total_count.scrape_total_count(out_path)
    out_path = os.path.join(out_dir, "aggregate.json")
    if not os.path.exists(out_path) or should_overwrite:
        success &= jhu_global_data.get_aggregate_data(out_path)
    out_path = os.path.join(out_dir, "freshness.json")
    if not os.path.exists(out_path) or should_overwrite:
        success &= calculate_data_freshness_per_country.get_freshness(out_path)

    return success


def generate_data(overwrite=False, quiet=False):
    if not quiet:
        print(
            "I need to generate the appropriate data, this is going to "
            "take a few minutes..."
        )
    generate_full_data.generate_data(
        os.path.join(self_dir, DAILIES_DIR),
        os.path.join(self_dir, COUNTRIES_DIR),
        overwrite=overwrite, quiet=quiet
    )

def compile_location_info(in_data, out_file,
                          keys=["country", "province", "city"], quiet=False):

    if not quiet:
        print("Exporting location info...")
    location_info = {}
    for item in in_data:
        geo_id = item['geoid']
        if geo_id not in location_info:
            name = str(item[keys[0]])
            # 2-letter ISO code for the country
            if name == "nan":
                code = ""
            else:
                code = country_converter.country_code_from_name(name)
            # Some special cases.
            if code == "" and item[keys[1]] == "Taiwan":
                code = "TW"
            if code == "":
                print("Oops, I couldn't find a code: " + str(item))
            location_info[geo_id] = [(str(item[key]) if str(item[key]) != "nan"
                                      else "") for key in
                                     [keys[2], keys[1]]] + [code]

    output = []
    for geoid in location_info:
        output.append(geoid + ":" + "|".join(location_info[geoid]))
    with open(out_file, "w") as f:
        f.write("\n".join(output))
        f.close()
