import requests
from dateutil import parser
from typing import Optional, Dict, List


class AirlineDataAPI:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "http://api.aviationstack.com/v1/flights"
        self.backup_data = self._load_backup_data()

        # ✅ Robust city → IATA mapping (expand as needed)
        self.city_to_iata = {
            "new york": "JFK",
            "los angeles": "LAX",
            "chicago": "ORD",
            "atlanta": "ATL",
            "dallas": "DFW",
            "london": "LHR",   # main, but could also be LGW, STN
            "paris": "CDG",    # main, could also be ORY
            "tokyo": "HND",
            "beijing": "PEK",
            "dubai": "DXB",
            "singapore": "SIN",
            "frankfurt": "FRA",
            "amsterdam": "AMS",
            "hong kong": "HKG",
            "sydney": "SYD",

            # 🇬🇧 UK
            "london": "LHR",  # main hub Heathrow
            "manchester": "MAN",
            "edinburgh": "EDI",
            "birmingham": "BHX",
            "glasgow": "GLA",

            # 🇫🇷 France
            "paris": "CDG",
            "nice": "NCE",
            "lyon": "LYS",
            "marseille": "MRS",

            # 🇩🇪 Germany
            "frankfurt": "FRA",
            "munich": "MUC",
            "berlin": "BER",
            "hamburg": "HAM",
            "dusseldorf": "DUS",

            # 🇳🇱 Netherlands
            "amsterdam": "AMS",

            # 🇪🇸 Spain
            "madrid": "MAD",
            "barcelona": "BCN",

            # 🇮🇹 Italy
            "rome": "FCO",
            "milan": "MXP",
            "venice": "VCE",

            # 🇨🇭 Switzerland
            "zurich": "ZRH",
            "geneva": "GVA",

            # 🇷🇺 Russia
            "moscow": "SVO",
            "st petersburg": "LED",

            # 🇨🇳 China
            "beijing": "PEK",
            "shanghai": "PVG",
            "guangzhou": "CAN",
            "shenzhen": "SZX",
            "chengdu": "CTU",
            "hong kong": "HKG",

            # 🇯🇵 Japan
            "tokyo": "HND",
            "osaka": "KIX",
            "nagoya": "NGO",

            # 🇰🇷 South Korea
            "seoul": "ICN",

            # 🇸🇬 Singapore
            "singapore": "SIN",

            # 🇦🇪 Middle East
            "dubai": "DXB",
            "abu dhabi": "AUH",
            "doha": "DOH",
            "istanbul": "IST",

            # 🇮🇳 India
            "delhi": "DEL",
            "mumbai": "BOM",
            "bangalore": "BLR",
            "chennai": "MAA",
            "hyderabad": "HYD",
            "kolkata": "CCU",

            # 🇦🇺 Australia
            "sydney": "SYD",
            "melbourne": "MEL",
            "brisbane": "BNE",
            "perth": "PER",

            # 🇧🇷 Brazil
            "sao paulo": "GRU",
            "rio de janeiro": "GIG",

            # 🇨🇦 Canada
            "toronto": "YYZ",
            "vancouver": "YVR",
            "montreal": "YUL",
        }

        # Build reverse map from backup data (IATA → city)
        self.airport_city_map = {
            airport['iata_code']: airport['city']
            for airport in self.backup_data['airports']
        }

    def _load_backup_data(self):
        return {
            "airlines": [
                {"name": "American Airlines", "iata_code": "AA"},
                {"name": "United Airlines", "iata_code": "UA"},
                {"name": "Delta Air Lines", "iata_code": "DL"},
            ],
            "airports": [
                {"name": "John F. Kennedy International", "iata_code": "JFK", "city": "New York"},
                {"name": "Los Angeles International", "iata_code": "LAX", "city": "Los Angeles"},
                {"name": "Chicago O'Hare International", "iata_code": "ORD", "city": "Chicago"},
                {"name": "Hartsfield-Jackson Atlanta International", "iata_code": "ATL", "city": "Atlanta"},
                {"name": "Dallas/Fort Worth International", "iata_code": "DFW", "city": "Dallas"}
            ],
            "sample_flights": [
                {
                    "flight_number": "AA123", "airline": "American Airlines",
                    "departure": {"airport": "JFK", "city": "New York", "time": "08:00"},
                    "arrival": {"airport": "LAX", "city": "Los Angeles", "time": "11:30"},
                    "status": "On Time", "aircraft": "Boeing 737-800"
                },
                {
                    "flight_number": "UA456", "airline": "United Airlines",
                    "departure": {"airport": "ORD", "city": "Chicago", "time": "14:20"},
                    "arrival": {"airport": "ATL", "city": "Atlanta", "time": "17:45"},
                    "status": "Delayed", "aircraft": "Airbus A320"
                },
                {
                    "flight_number": "DL789", "airline": "Delta Air Lines",
                    "departure": {"airport": "ATL", "city": "Atlanta", "time": "09:15"},
                    "arrival": {"airport": "JFK", "city": "New York", "time": "12:30"},
                    "status": "On Time", "aircraft": "Boeing 757-200"
                }
            ]
        }

    def make_api_request(self, params: Dict) -> Optional[Dict]:
        if not self.api_key:
            print("💡 No API key provided. Using local backup data.")
            return None
        try:
            params['access_key'] = self.api_key
            print(f"✈️ Making live API call to AviationStack with params: {params}")
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if 'error' in data:
                print(f"❌ API Error: {data['error']['info']}")
                return None
            return data
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            return None

    def search_flights(self, departure_city: str = None, arrival_city: str = None,
                       flight_number: str = None) -> List[Dict]:
        params = {'limit': 10}
        if flight_number:
            params['flight_iata'] = flight_number.upper()
        elif departure_city and arrival_city:
            params['dep_iata'] = self.get_airport_code(departure_city)
            params['arr_iata'] = self.get_airport_code(arrival_city)

        if self.api_key and (flight_number or (departure_city and arrival_city)):
            api_data = self.make_api_request(params)
            if api_data and 'data' in api_data and api_data['data']:
                print(f"✅ Found {len(api_data['data'])} flights from live API.")
                return self._format_api_flight_data(api_data['data'])

        print("🟡 Could not fetch from API or not enough info. Searching local backup data.")
        return self._search_backup_flights(departure_city, arrival_city, flight_number)

    def _format_api_flight_data(self, api_flights: List[Dict]) -> List[Dict]:
        formatted_flights = []
        for flight in api_flights:
            try:
                departure_info = flight.get('departure') or {}
                arrival_info = flight.get('arrival') or {}
                airline_info = flight.get('airline') or {}
                flight_info = flight.get('flight') or {}
                aircraft_info = flight.get('aircraft') or {}

                dep_iata = departure_info.get('iata', 'N/A')
                arr_iata = arrival_info.get('iata', 'N/A')

                dep_time_str = departure_info.get('scheduled')
                arr_time_str = arrival_info.get('scheduled')
                dep_time = parser.parse(dep_time_str).strftime('%H:%M') if dep_time_str else "N/A"
                arr_time = parser.parse(arr_time_str).strftime('%H:%M') if arr_time_str else "N/A"

                formatted_flight = {
                    'flight_number': flight_info.get('iata', 'N/A'),
                    'airline': airline_info.get('name', 'Unknown'),
                    'departure': {
                        'airport': dep_iata,
                        'city': self.airport_city_map.get(dep_iata, dep_iata),
                        'time': dep_time
                    },
                    'arrival': {
                        'airport': arr_iata,
                        'city': self.airport_city_map.get(arr_iata, arr_iata),
                        'time': arr_time
                    },
                    'status': flight.get('flight_status', 'Unknown').replace('_', ' ').title(),
                    'aircraft': aircraft_info.get('registration', 'Unknown')
                }
                formatted_flights.append(formatted_flight)
            except Exception as e:
                print(f"⚠️ Error formatting flight data for one flight: {e}")
                continue

        return formatted_flights

    def _search_backup_flights(self, departure_city: str = None, arrival_city: str = None,
                               flight_number: str = None) -> List[Dict]:
        results = []
        for flight in self.backup_data['sample_flights']:
            match = True
            if flight_number:
                match = flight['flight_number'].upper() == flight_number.upper()
            else:
                if departure_city:
                    match = match and (departure_city.lower() in flight['departure']['city'].lower() or
                                       departure_city.upper() == flight['departure']['airport'])
                if arrival_city:
                    match = match and (arrival_city.lower() in flight['arrival']['city'].lower() or
                                       arrival_city.upper() == flight['arrival']['airport'])
            if match:
                results.append(flight)
        return results

    def get_airport_code(self, city_or_code: str) -> str:
        """
        Tries to resolve user input into a valid IATA code.
        Order of checks:
        1. Already a 3-letter code.
        2. Known city → IATA dictionary.
        3. Backup airport list.
        4. Fallback: uppercase the input.
        """
        if not city_or_code:
            return "N/A"

        if len(city_or_code) == 3 and city_or_code.isupper():
            return city_or_code

        # ✅ Step 2: Check dictionary
        if city_or_code.lower() in self.city_to_iata:
            return self.city_to_iata[city_or_code.lower()]

        # ✅ Step 3: Check backup data
        for airport in self.backup_data['airports']:
            if city_or_code.lower() in airport['city'].lower():
                return airport['iata_code']

        # ✅ Step 4: Fallback
        return city_or_code.upper()

    def search_routes(self, departure: str, arrival: str) -> List[Dict]:
        return self.search_flights(departure_city=departure, arrival_city=arrival)

    def get_popular_destinations(self) -> List[str]:
        return [airport['city'] for airport in self.backup_data['airports']]

    def get_flight_status(self, flight_number: str) -> Optional[Dict]:
        """
        Look up the status of a specific flight by flight number.
        Checks live API first, then backup data.
        """
        if not flight_number:
            return None

        # First try live API
        if self.api_key:
            params = {"flight_iata": flight_number.upper(), "limit": 1}
            api_data = self.make_api_request(params)
            if api_data and 'data' in api_data and api_data['data']:
                flight = self._format_api_flight_data(api_data['data'])[0]
                return {
                    "flight_number": flight['flight_number'],
                    "airline": flight['airline'],
                    "departure": flight['departure'],
                    "arrival": flight['arrival'],
                    "status": flight['status']
                }

        # Fallback to backup data
        for flight in self.backup_data['sample_flights']:
            if flight['flight_number'].upper() == flight_number.upper():
                return {
                    "flight_number": flight['flight_number'],
                    "airline": flight['airline'],
                    "departure": flight['departure'],
                    "arrival": flight['arrival'],
                    "status": flight['status']
                }

        return None


class MockBookingSystem:
    def __init__(self):
        # Preloaded demo bookings
        self.bookings = {
            'ABC123': {
                'booking_id': 'ABC123',
                'passenger_name': 'John Smith',
                'flight_number': 'AA123',
                'departure': 'New York (JFK)',
                'arrival': 'Los Angeles (LAX)',
                'date': '2024-09-15',
                'seat': '12A',
                'status': 'Confirmed'
            },
            'DEF456': {
                'booking_id': 'DEF456',
                'passenger_name': 'Jane Doe',
                'flight_number': 'UA456',
                'departure': 'Chicago (ORD)',
                'arrival': 'Atlanta (ATL)',
                'date': '2024-09-16',
                'seat': '8B',
                'status': 'Confirmed'
            },
            'GHI789': {
                'booking_id': 'GHI789',
                'passenger_name': 'Bob Johnson',
                'flight_number': 'DL789',
                'departure': 'Atlanta (ATL)',
                'arrival': 'New York (JFK)',
                'date': '2024-09-17',
                'seat': '15C',
                'status': 'Pending'
            }
        }

    def find_booking(self, booking_id: str) -> Optional[Dict]:
        """Look up a booking by its unique ID"""
        return self.bookings.get(booking_id.upper())

    def search_bookings_by_name(self, passenger_name: str) -> List[Dict]:
        """Find all bookings that match a passenger name"""
        results = []
        for booking in self.bookings.values():
            if passenger_name.lower() in booking['passenger_name'].lower():
                results.append(booking)
        return results

    def create_booking(self, passenger_name: str, flight_number: str,
                       departure: str, arrival: str, date: str, seat: str) -> Dict:
        """Create a new mock booking and return it"""
        new_id = f"BK{len(self.bookings) + 1:03d}"
        booking = {
            'booking_id': new_id,
            'passenger_name': passenger_name,
            'flight_number': flight_number,
            'departure': departure,
            'arrival': arrival,
            'date': date,
            'seat': seat,
            'status': 'Confirmed'
        }
        self.bookings[new_id] = booking
        return booking
