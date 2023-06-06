import requests
import json
import argparse
import datetime
from tqdm import tqdm
from prettytable import PrettyTable
import concurrent.futures

parser = argparse.ArgumentParser()

# Add origin and destination airports as positional arguments
parser.add_argument('origin', type=str, help="Origin airport code")
parser.add_argument('destination', type=str, help="Destination airport code")
parser.add_argument('date', type=str,
                    help="Departure date to start searching from (YYYY-MM-DD)")
parser.add_argument('-d', '--days', type=int, default=10,
                     help="Number of days to search for after the initial departure date")
parser.add_argument('--mile_value', type=float,
                    default=0.0210, help="Value of a mile in BRL")
parser.add_argument('--adults', type=int, default=1)

args = parser.parse_args()


with open('smiles.json', 'r') as f:
    config = json.load(f)

params = config["url_params"]
params["destinationAirportCode"] = args.destination
params["originAirportCode"] = args.origin
params["adults"] = args.adults

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
print ("Number of adults: %s" % args.adults)

print("Retrieving flights...")

# Define a function to send a request and return the response
def send_request(param):
    return requests.get(config["url"], headers=config["headers"], params=param).text

# Create a thread pool with a maximum of 10 workers
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    # Submit each request to the executor and store the futures
    futures = [executor.submit(send_request, param) for param in all_params]
    # Iterate over the futures as they are completed and store the results
    for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
        responses.append(future.result())

#dump responses to file
with open('data/responses.json', 'w') as f:
    json.dump(responses, f)
#with open('data/responses.json', 'r') as f:
#    responses = json.load(f)

best_fares = {}

for response in responses:
    response = json.loads(response)
    dct = response.get("requestedFlightSegmentList", [{}])[0]
    if "flightList" in dct:
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
                fare_value = fare["money"] + (fare["miles"] * args.mile_value) + fare["airlineTax"]                
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

# sort table by total value and cabin
table.sortby = "Total Value"
table.float_format = ".2"
table.reversesort = False

print(table)

# Save the table as a HTML page, with sorting enabled on columns
with open('flightsearch/%s_%s_%s_%s.html' % (args.origin, args.destination, args.date, args.days), 'w') as f:
    # Add the header.html file to the top of the page
    with open('header.html', 'r') as header:
        f.write(header.read())
    f.write(table.get_html_string(attributes={"name":"BUGA", "class":"sortable_table"}, sortby="Total Value", reversesort=False))
    
    # Generate the footer, adding the current date and time
    with open('footer.html', 'r') as footer:
        f.write(footer.read().replace("{{date}}", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
