## Service overview:
The service is a webapp with a very normal structure. Templates are in *dieSchablonen*, static files in *statisch* and routes in *dieRouten.py*. It uses sqlite3.

Users can register and log in, and have a Profile page which they can edit to include a description.
There is a Contact and Feedback form at */dasKontaktformular* because every good service providing website needs one :)
Existing flights are listed at */dieFlüge* and new ones can be created through */dieFlugerstellung*.

When creating a flight (or booking onto one) you receive a Ticket which you can view on your Profile at */dasProfil*. Users that have VIP tickets will be able to see VIP boarding information when accessing the flight.

## Exploit overview:
### Forging JSON Web Token (CVE-2022-39227):
The vulnerability is the outdated version of the python_jwt library. Given a valid token, you're able to re-use its signature with a different payload. 

Through this you're able to book onto a flight, and then alter the ticket to give yourself VIP access. This way you'll be able to see the VIP boarding information field in which the gameserver will store flags.