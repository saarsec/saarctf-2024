import gamelib
from gamelib import *
import sys
import random
import datetime
import re
import urllib3


# See the "SampleServiceInterface" from gamelib for a bigger example
# See https://gitlab.saarsec.rocks/saarctf/gamelib/-/blob/master/docs/howto_checkers.md for documentation.

class ExampleServiceInterface(ServiceInterface):
    name = 'Deutsches Flugzeug'
    flag_id_types = ['username']
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def check_integrity(self, team: Team, tick: int):
        PORT = 5000
        # Check for registration and login
        password = usernames.generate_password()
        username = usernames.generate_name()
        print(f"Using username: {username} and password: {password}")
        reg = {"username": username, "email": "user@test.gameserver", "password": password}
        sess = Session()
        print("[Registering]")
        sess.post(f"https://{team.ip}:{PORT}/auth/signup", data = reg, verify=False, timeout=TIMEOUT)
        reg = {"username": username, "password": password}
        print("[Logging In]")
        sess.post(f"https://{team.ip}:{PORT}/auth/login", data = reg, verify=False, timeout=TIMEOUT)
        res = sess.get(f"https://{team.ip}:{PORT}", verify=False, timeout=TIMEOUT)
        assert "airport1.jpeg" in res.text, "Benutzer konnte sich nicht anmelden oder registrieren!"

        # Check profile page:
        print("[Creating Profile]")
        res = sess.get(f"https://{team.ip}:{PORT}/dasProfil", verify=False, timeout=TIMEOUT)
        assert username in res.text, "Profilseite konnte nicht erreicht werden!"

        # Check flight creation
        print("[Creating Flight]")
        res = sess.get(f"https://{team.ip}:{PORT}/dieFlugerstellung", verify=False, timeout=TIMEOUT)
        assert "Flugbeschreibung" in res.text, "Flugerstellungsseite konnte nicht erreicht werden!"
        von = random.choice(list(country_dict.keys()))
        zu = random.choice(list(country_dict.keys()))
        post_data = {
            "beschreibung": f"Flug von {von} nach {zu}",
            "von": von,
            "zu": zu,
            "vip_info": "I hope this will stay secret :)",
            "anzahl": random.randint(1,20),
            "wichtig": random.randint(1,5),
            "datum": datetime.datetime.now().isoformat(sep="T", timespec="minutes"),
            "passwort": password
        }
        print("[Retrieving Flight]")
        res = sess.post(f"https://{team.ip}:{PORT}/dieFlugerstellung", data = post_data, verify=False, timeout=TIMEOUT)
        pattern = r"ID: </strong>(\d*)</p>"
        try:
            flug_id = re.search(pattern, res.text).group(1)
        except:
            print(res.text)
        assert username in res.text, "Erstellter Flug konnte nicht abgerufen werden!"

        #Check Flight booking
        print("[Booking Flight]")
        res = sess.post(f"https://{team.ip}:{PORT}/dasBuchen/{flug_id}", verify=False, timeout=TIMEOUT)
        assert "Nutzerinformationen ändern" in res.text, "Flug konnte nicht gebucht werden!"

        # Check flight search page
        print("[Searching for Created Flight]")
        for page in range(10):
            res = sess.get(f"https://{team.ip}:{PORT}/dieFlüge/{page}", verify=False, timeout=TIMEOUT)
            if username in res.text:
                break
        else:
            assert False, "Ein Flug konnte nicht erstellt oder gefunden werden!"

        print("[Finished Integrity Check]")
        sess.close()
        
        




    def store_flags(self, team: Team, tick: int):
        PORT = 5000
        flag = self.get_flag(team, tick)
        password = usernames.generate_password()
        username = self.get_flag_id(team, tick, 0)
        print(f"Using username: {username} and password: {password}")
        reg = {"username": username, "email": "user@test.gameserver", "password": password}
        sess = Session()
        print("[Registering]")
        res = sess.post(f"https://{team.ip}:{PORT}/auth/signup", data=reg, verify=False, timeout=TIMEOUT)
        if "Username already taken!" in res.text:
            try:
                data = self.load(team, tick, "creds")
                username, password, _ = data
                print(f"Username was already used changing to previous account: {username}:{password}")
            except TypeError:
                raise FlagMissingException("Flaggen konnte nicht gefunden werden!")

        reg = {"username": username, "password": password}
        print("[Logging In]")
        sess.post(f"https://{team.ip}:{PORT}/auth/login", data=reg, verify=False, timeout=TIMEOUT)
        res = sess.get(f"https://{team.ip}:{PORT}", verify=False, timeout=TIMEOUT)
        print("[Creating Flight]")
        res = sess.get(f"https://{team.ip}:{PORT}/dieFlugerstellung", verify=False, timeout=TIMEOUT)
        von = random.choice(list(country_dict.keys()))
        zu = random.choice(list(country_dict.keys()))
        post_data = {
            "beschreibung": f"Flug von {von} nach {zu}",
            "von": von,
            "zu": zu,
            "vip_info": flag,
            "anzahl": random.randint(1, 20),
            "wichtig": random.randint(1, 5),
            "datum": datetime.datetime.now().isoformat(sep="T", timespec="minutes"),
            "passwort": password
        }
        print("[Retrieving Flight]")
        res = sess.post(f"https://{team.ip}:{PORT}/dieFlugerstellung", data=post_data, verify=False, timeout=TIMEOUT)
        
        self.store(team, tick, "creds", [username, password, res.url])
        sess.close()
        print("[Finished Flag Store]")


    def retrieve_flags(self, team: Team, tick: int):
        PORT = 5000
        flag = self.get_flag(team, tick)
        try:
            data = self.load(team, tick, "creds")
            username, password, url = data
        except TypeError:
            raise FlagMissingException("Flaggen konnte nicht gefunden werden!")
        print(f"Using username: {username} and password: {password}")
        print(url)
        reg = {"username": username, "password": password}
        print("[Logging In]")
        sess = Session()
        sess.post(f"https://{team.ip}:{PORT}/auth/login", data=reg, verify=False, timeout=TIMEOUT)
        url = url.split("derFlug/")[1]
        res = sess.get(f"https://{team.ip}:{PORT}/derFlug/{url}", verify=False, timeout=TIMEOUT)
        if flag not in res.text:
            # verbose error logging is always a good idea
            print('GOT:', res.text)
            # flag not found? Raise FlagMissingException
            raise FlagMissingException("Flaggen konnte nicht gefunden werden!")
        sess.close()
        print("[Finished Flag Receive]")

country_dict = {
    "Afghanistan": "KBL",
    "Ägypten": "CAI",
    "Albanien": "TIA",
    "Algerien": "ALG",
    "Andorra": "ALV",  # Placeholder code for Andorra
    "Angola": "LAD",
    "Antigua und Barbuda": "ANU",
    "Argentinien": "EZE",
    "Armenien": "EVN",
    "Australien": "SYD",
    "Österreich": "VIE",
    "Aserbaidschan": "GYD",
    "Bahamas": "NAS",
    "Bahrain": "BAH",
    "Bangladesch": "DAC",
    "Barbados": "BGI",
    "Weißrussland": "MSQ",
    "Belgien": "BRU",
    "Belize": "BZE",
    "Benin": "COO",
    "Bhutan": "PBH",
    "Bolivien": "VVI",
    "Bosnien und Herzegowina": "SJJ",
    "Botswana": "GBE",
    "Brasilien": "GRU",
    "Brunei": "BWN",
    "Bulgarien": "SOF",
    "Burkina Faso": "OUA",
    "Burundi": "BJM",
    "Cabo Verde": "SID",
    "Kambodscha": "PNH",
    "Kamerun": "DLA",
    "Kanada": "YYZ",
    "Zentralafrikanische Republik": "BGF",
    "Tschad": "NDJ",
    "Chile": "SCL",
    "China": "PEK",
    "Kolumbien": "BOG",
    "Komoren": "HAH",
    "Costa Rica": "SJO",
    "Kroatien": "ZAG",
    "Kuba": "HAV",
    "Zypern": "LCA",
    "Tschechische Republik": "PRG",
    "Demokratische Republik Kongo": "FIH",
    "Dänemark": "CPH",
    "Dschibuti": "JIB",
    "Dominica": "DOM",
    "Dominikanische Republik": "SDQ",
    "Ecuador": "UIO",
    "El Salvador": "SAL",
    "Äquatorialguinea": "SSG",
    "Eritrea": "ASM",
    "Estland": "TLL",
    "Eswatini": "SZK",
    "Äthiopien": "ADD",
    "Fidschi": "NAN",
    "Finnland": "HEL",
    "Frankreich": "CDG",
    "Gabun": "LBV",
    "Gambia": "BJL",
    "Georgien": "TBS",
    "Deutschland": "FRA",
    "Ghana": "ACC",
    "Griechenland": "ATH",
    "Grenada": "GND",
    "Guatemala": "GUA",
    "Guinea": "CKY",
    "Guinea-Bissau": "OXB",
    "Guyana": "GEO",
    "Haiti": "PAP",
    "Honduras": "TGU",
    "Ungarn": "BUD",
    "Island": "KEF",
    "Indien": "DEL",
    "Indonesien": "CGK",
    "Iran": "IKA",
    "Irak": "BGW",
    "Irland": "DUB",
    "Israel": "TLV",
    "Italien": "FCO",
    "Elfenbeinküste": "ABJ",
    "Jamaika": "KIN",
    "Japan": "HND",
    "Jordanien": "AMM",
    "Kasachstan": "ALA",
    "Kenia": "NBO",
    "Kiribati": "TRW",
    "Kuwait": "KWI",
    "Kirgisistan": "FRU",
    "Laos": "VTE",
    "Lettland": "RIX",
    "Libanon": "BEY",
    "Lesotho": "MSU",
    "Liberia": "ROB",
    "Libyen": "TIP",
    "Liechtenstein": "ACH",  # Placeholder code for Liechtenstein
    "Litauen": "VNO",
    "Luxemburg": "LUX",
    "Madagaskar": "TNR",
    "Malawi": "LLW",
    "Malaysia": "KUL",
    "Malediven": "MLE",
    "Mali": "BKO",
    "Malta": "MLA",
    "Marshallinseln": "MAJ",
    "Mauretanien": "NKC",
    "Mauritius": "MRU",
    "Mexiko": "MEX",
    "Mikronesien": "PNI",
    "Moldawien": "KIV",
    "Monaco": "MCM",
    "Mongolei": "ULN",
    "Montenegro": "TGD",
    "Marokko": "CMN",
    "Mosambik": "MPM",
    "Myanmar": "RGN",
    "Namibia": "WDH",
    "Nauru": "INU",
    "Nepal": "KTM",
    "Niederlande": "AMS",
    "Neuseeland": "AKL",
    "Nicaragua": "MGA",
    "Niger": "NIM",
    "Nigeria": "LOS",
    "Nordkorea": "FNJ",
    "Nordmazedonien": "SKP",
    "Norwegen": "OSL",
    "Oman": "MCT",
    "Pakistan": "ISB",
    "Palau": "ROR",
    "Panama": "PTY",
    "Papua-Neuguinea": "POM",
    "Paraguay": "ASU",
    "Peru": "LIM",
    "Philippinen": "MNL",
    "Polen": "WAW",
    "Portugal": "LIS",
    "Katar": "DOH",
    "Republik Kongo": "BZV",
    "Rumänien": "OTP",
    "Russland": "SVO",
    "Ruanda": "KGL",
    "St. Kitts und Nevis": "SKB",
    "St. Lucia": "UVF",
    "St. Vincent und die Grenadinen": "SVD",
    "Samoa": "APW",
    "San Marino": "RMI",
    "São Tomé und Príncipe": "TMS",
    "Saudi-Arabien": "JED",
    "Senegal": "DKR",
    "Serbien": "BEG",
    "Seychellen": "SEZ",
    "Sierra Leone": "FNA",
    "Singapur": "SIN",
    "Slowakei": "BTS",
    "Slowenien": "LJU",
    "Salomonen": "HIR",
    "Somalia": "MGQ",
    "Südafrika": "JNB",
    "Südkorea": "ICN",
    "Südsudan": "JUB",
    "Spanien": "MAD",
    "Sri Lanka": "CMB",
    "Sudan": "KRT",
    "Suriname": "PBM",
    "Schweden": "ARN",
    "Schweiz": "ZRH",
    "Syrien": "DAM",
    "Taiwan": "TPE",
    "Tadschikistan": "DYU",
    "Tansania": "JRO",
    "Thailand": "BKK",
    "Timor-Leste": "DIL",
    "Togo": "LFW",
    "Tonga": "TBU",
    "Trinidad und Tobago": "POS",
    "Tunesien": "TUN",
    "Türkei": "IST",
    "Turkmenistan": "ASB",
    "Tuvalu": "FUN",
    "Uganda": "EBB",
    "Ukraine": "KBP",
    "Vereinigte Arabische Emirate": "DXB",
    "Vereinigtes Königreich": "LHR",
    "Vereinigte Staaten": "ATL",
    "Uruguay": "MVD",
    "Usbekistan": "TAS",
    "Vanuatu": "VLI",
    "Vatikanstadt": "CIA",
    "Venezuela": "CCS",
    "Vietnam": "SGN",
    "Jemen": "SAH",
    "Sambia": "LUN",
    "Simbabwe": "HRE",
}


if __name__ == '__main__':
    # USAGE: python3 interface.py                      # test against localhost
    # USAGE: python3 interface.py 1.2.3.4              # test against IP
    # USAGE: python3 interface.py 1.2.3.4 retrieve     # retrieve last 10 ticks (for exploits relying on checker interaction)
    # (or use gamelib/run-checkers to test against docker container)

    team = Team(1, 'TestTeam', sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1')
    service = ExampleServiceInterface(1)

    if len(sys.argv) > 2 and sys.argv[2] == 'retrieve':
        for tick in range(1, 10):
            try:
                service.retrieve_flags(team, tick)
            except:
                pass
        sys.exit(0)

    for tick in range(1, 4):
        print(f'\n\n=== TICK {tick} ===')
        service.check_integrity(team, tick)
        service.store_flags(team, tick)
        service.retrieve_flags(team, tick)


