import azure.functions as func
import logging
import requests
import json
from azure.cosmos import CosmosClient, PartitionKey

# Cosmos DB connection details
COSMOS_ENDPOINT = "https://<your-cosmos-db-name>.documents.azure.com:443/"
COSMOS_KEY = "<your-cosmos-db-key>"
DATABASE_NAME = "UserDataDB"
CONTAINER_NAME = "UserLocations"

# Initialize Cosmos DB Client
client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="website_user_data")
def website_user_data(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to fetch the user's IP address from the request headers,
    get location data, and store it in Cosmos DB.
    """
    try:
        logging.info("Processing request to fetch user IP address and location details.")

        # Fetch the IP from common headers
        client_ip = req.headers.get("X-Forwarded-For") or req.headers.get("X-Real-IP")
        if not client_ip:
            client_ip = req.remote_addr

        if client_ip:
            # Use the first IP if multiple are present
            client_ip = client_ip.split(",")[0].strip()
            logging.info(f"Client IP resolved: {client_ip}")
            
            # Fetch IP details from ipinfo.io
            url = f"http://ipinfo.io/{client_ip}/json?token=<your-ipinfo-token>"
            response = requests.get(url)

            if response.status_code == 200:
                ip_details = response.json()
                ip_city = ip_details.get("city", "Unknown")
                ip_region = ip_details.get("region", "Unknown")
                ip_country = ip_details.get("country", "Unknown")
                ip_location = f"{ip_city}, {ip_region}, {ip_country}"

                # Prepare the document to insert into Cosmos DB
                document = {
                    "id": client_ip,  # Use the IP as the document ID
                    "ip": client_ip,
                    "city": ip_city,
                    "region": ip_region,
                    "country": ip_country,
                    "location": ip_location,
                }

                # Insert document into Cosmos DB
                container.upsert_item(document)
                logging.info(f"Data inserted for IP: {client_ip}")

                # Return JSON response
                return func.HttpResponse(
                    json.dumps(document),
                    mimetype="application/json",
                    status_code=200
                )
            else:
                logging.error(f"Failed to fetch IP details for {client_ip}.")
                return func.HttpResponse(
                    json.dumps({"error": f"Failed to fetch details for IP: {client_ip}"}),
                    mimetype="application/json",
                    status_code=502
                )
        else:
            logging.warning("Client IP could not be determined.")
            return func.HttpResponse(
                json.dumps({"error": "Could not determine IP address."}),
                mimetype="application/json",
                status_code=400
            )

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred."}),
            mimetype="application/json",
            status_code=500
        )
