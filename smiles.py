import requests
import json
import argparse
import datetime
from tqdm import tqdm
from prettytable import PrettyTable

parser = argparse.ArgumentParser()

# Add origin and destination airports as positional arguments
parser.add_argument('origin', type=str, help="Origin airport code")
parser.add_argument('destination', type=str, help="Destination airport code")
parser.add_argument('date', type=str,
                    help="Departure date to start searching from (YYYY-MM-DD)")
parser.add_argument('-d', '--days', type=int, default=10,
                     help="Number of days to search for after the initial departure date")
parser.add_argument('--mile_value', type=float,
                    default=0.0175, help="Value of a mile in BRL")

args = parser.parse_args()


with open('smiles.json', 'r') as f:
    config = json.load(f)

params = config["url_params"]
params["destinationAirportCode"] = args.destination
params["originAirportCode"] = args.origin

all_dates = [args.date]
for i in range(1, args.days):
    all_dates.append((datetime.datetime.strptime(args.date, "%Y-%m-%d") +
                      datetime.timedelta(days=i)).strftime("%Y-%m-%d"))

all_params = []
for date in all_dates:
    params_copy = params.copy()
    params_copy.update({"departureDate": date})
    all_params.append(params_copy)

responses = []
print ("-- SMILES AIRLINE FARES --")
print ("Departure date: %s" % args.date)
print ("Number of days to search: %s" % args.days)
print ("Origin: %s" % args.origin)
print ("Destination: %s" % args.destination)
print ("Mile value: %s" % args.mile_value)

print ("Retrieving flights...")
for param in tqdm(all_params):
    response = requests.get(config["url"], headers=config["headers"], params=param).text
    responses.append(response)

#dump responses to file
with open('data/responses.json', 'w') as f:
    json.dump(responses, f)
with open('data/responses.json', 'r') as f:
    responses = json.load(f)

best_fares = {}

for response in responses:
    dct = json.loads(response)["requestedFlightSegmentList"][0]
    if dct["flightList"]:
        for flight in dct["flightList"]:
            date = flight["departure"]["date"].split("T")[0]
            time = flight["departure"]["date"].split("T")[1]
            airline = flight["airline"]["code"]
            cabin = flight["cabin"]
            if date not in best_fares:
                 best_fares[date] = {}
            if cabin not in best_fares[date]:
                best_fares[date][cabin] = {}

            #print ("Date: %s, Time: %s, Airline: %s, Cabin: %s" % (date, time, airline, cabin))
            best_fare_type = ""
            for fare in flight["fareList"]:
                fare_type = fare["type"]
                fare_value = fare["money"] + (fare["miles"] * 0.0175) + fare["airlineTax"]                
                #print ("Fare Type: %s, Fare Value: %s" % (fare_type, fare_value))
                if best_fares[date][cabin] == {} or fare_value < best_fares[date][cabin]["total_value"]:
                    best_fares[date][cabin] = {"fare_type": fare_type, "total_value": fare_value, "airline": airline}

table = PrettyTable()
table.field_names = ["Date", "Cabin", "Fare Type", "Total Value", "Airline"]

for date, classes in best_fares.items():
    for cabin, values in classes.items():
        fare_type = values['fare_type']
        total_value = values['total_value']
        airline = values['airline']
        table.add_row([date, cabin, fare_type, total_value, airline])

table.sortby = "Total Value"
table.float_format = ".2"
table.reversesort = False

print(table)
