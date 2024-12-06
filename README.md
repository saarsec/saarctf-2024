# saarCTF 2024

Services from [saarCTF 2024](https://ctftime.org/event/2490).

## Building services
Enter a service directory and use `docker compose`, e.g.:
```bash
cd 8-bit-oracle
docker compose up --build -d
```

## Prepare checker environment
In the root directory, run:
```shell
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

## Running checkers
Every service comes with a `checkers` directory, which contains a python-script named after the service.
Running this script should place three flags in the service and try to retrieve them subsequently.
Caveat: Make sure the `gamelib` is in the `PYTHONPATH`, e.g.:
```bash
cd 8-bit-oracle/checkers/
PYTHONPATH=.. python3 8-bit-oracle.py [<ip>]
```

Checkers require a Redis instance to store information between ticks. 
If you don't have redis installed locally, use the environment variables `REDIS_HOST` and `REDIS_DB` to configure one.


## Flag IDs and exploits
The script `get_flag_ids.py` prints you the flag ids used to store the demo flags.

Each service comes with demo exploits to show the vulnerability.
To run an exploit: `python3 exploit_file.py <ip> [<flag-id>]`


## Services
- [8-Bit-Oracle](./8-bit-oracle) | [Exploits](./8-bit-oracle/exploits)
- [BTX](./btx) | [Exploits](./btx/exploits)
- [Certified Transparency](./certified-transparency) | [Exploits](./certified-transparency/exploits)
- [Deutsches Flugzeug](./deutsches-flugzeug) | [Exploits](./deutsches-flugzeug/exploits)
- [Rent-a-Printer](./rent-a-printer) | [Exploits](./rent-a-printer/exploits)
- [Reversaar](./reversaar) | [Exploits](./reversaar/exploits)


## Remarks for Rent-A-Printer
- Your local cups might block one of the service ports (tcp 631). Run `systemctl stop cups` if necessary.
- The cups-browsed service does not start in the docker container, thus, one exploit does not work. Try it against the full VM.
