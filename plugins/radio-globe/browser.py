"""Radio Browser discovery, bounded HTTP reads and sanitized public records."""
import json
from pathlib import Path
import random
import re
import signal
import socket
import time
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from storage import folder, read, write

AGENT = 'EitrRadioGlobe/1.0'
LIMIT = 50
LOCATIONS = json.loads((Path(__file__).parent / 'data/countries.json').read_text())


def text(value, limit=160):
    return ''.join(character if character.isprintable() else ' ' for character in str(value or ''))[:limit].strip()


def stream_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(character.isspace() or ord(character) < 32 for character in value):
        return ''
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
            return ''
        parsed.port
    except ValueError:
        return ''
    return value


def station(record):
    if not isinstance(record, dict) or record.get('lastcheckok') != 1:
        return None
    address = stream_url(record.get('url_resolved')) or stream_url(record.get('url'))
    identifier = record.get('stationuuid', '')
    if not address or not isinstance(identifier, str) or not re.fullmatch(r'[a-zA-Z0-9-]{1,64}', identifier):
        return None
    try:
        bitrate = max(0, min(10000, int(record.get('bitrate') or 0)))
    except (TypeError, ValueError):
        bitrate = 0
    return dict(stationuuid=identifier, name=text(record.get('name')) or 'Unnamed station',
                tags=text(record.get('tags')), codec=text(record.get('codec'), 24), bitrate=bitrate,
                countrycode=text(record.get('countrycode'), 2), url=address, lastcheckok=1)


def deadline(signum, frame):
    raise RuntimeError('The request timed out. Check your connection and retry.')


def json_request(address):
    request = Request(address, headers={'User-Agent': AGENT, 'Accept': 'application/json'})
    with urlopen(request, timeout=2.0) as response:
        payload = response.read(2 * 1024 * 1024 + 1)
    if len(payload) > 2 * 1024 * 1024:
        raise ValueError('Radio Browser response is too large')
    result = json.loads(payload)
    if not isinstance(result, list):
        raise ValueError('Radio Browser returned an invalid list')
    return result


def servers():
    # DNS discovery is the documented server list, not a pinned mirror.
    addresses = {entry[4][0] for entry in socket.getaddrinfo('all.api.radio-browser.info', 443, type=socket.SOCK_STREAM)}
    names = set()
    for address in sorted(addresses)[:8]:
        try:
            hostname = socket.gethostbyaddr(address)[0].rstrip('.').lower()
            if re.fullmatch(r'[a-z0-9-]+\.api\.radio-browser\.info', hostname):
                names.add('https://' + hostname)
                continue
        except OSError:
            pass
        # HTTPS certificates generally need the reverse-DNS name; skip unresolved IPs.
    result = list(names)
    random.shuffle(result)
    return result


def request(path, parameters=None):
    previous = signal.signal(signal.SIGALRM, deadline)
    started = time.monotonic()
    previous_timer = signal.setitimer(signal.ITIMER_REAL, 7.0)
    try:
        for server in servers():
            try:
                return json_request(server + path + ('?' + urlencode(parameters) if parameters else ''))
            except (OSError, ValueError):
                continue
        raise RuntimeError('Radio Browser is unavailable. Check your connection and retry.')
    except OSError as error:
        raise RuntimeError('Radio Browser is unavailable. Check your connection and retry.') from error
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if previous_timer[0]:
            signal.setitimer(signal.ITIMER_REAL, max(0.01, previous_timer[0] - (time.monotonic() - started)))


def located(countries):
    """Each country with its bundled marker, read now so a plugin update moves cached dots too."""
    return [dict(country, location=LOCATIONS.get(country.get('code'))) for country in countries if isinstance(country, dict)]


def countries():
    path = folder('CACHE') / 'countries.json'
    cached = read(path, {})
    if isinstance(cached, dict) and 0 <= time.time() - cached.get('saved', 0) < 86400:
        return dict(countries=located(cached.get('countries', [])), stale=False)
    try:
        records = request('/json/countries', {'hidebroken': 'true'})
        result = []
        for record in records:
            if not isinstance(record, dict):
                continue
            code = str(record.get('iso_3166_1', '')).upper()
            try:
                count = int(record.get('stationcount', 0))
            except (TypeError, ValueError):
                continue
            if re.fullmatch('[A-Z]{2}', code) and count > 0:
                result.append(dict(code=code, name=text(record.get('name')), count=count))
        result.sort(key=lambda country: country['name'].casefold())
        write(path, dict(saved=time.time(), countries=result))
        return dict(countries=located(result), stale=False)
    except RuntimeError:
        if isinstance(cached, dict) and cached.get('countries'):
            return dict(countries=located(cached['countries']), stale=True)
        raise


def stations(mode, value, offset=0):
    if mode not in ('country', 'name', 'tag') or not isinstance(value, str) or len(value) > 100:
        raise ValueError('Invalid station search')
    if mode == 'country' and not re.fullmatch('[A-Z]{2}', value):
        raise ValueError('Invalid country code')
    parameters = dict(hidebroken='true', limit=LIMIT, offset=max(0, int(offset)), order='votes', reverse='true')
    path = '/json/stations/bycountrycodeexact/' + quote(value, safe='') if mode == 'country' else '/json/stations/search'
    if mode != 'country':
        parameters[mode] = value
    records = request(path, parameters)
    cleaned = [entry for record in records if (entry := station(record)) is not None]
    return dict(stations=cleaned, more=len(records) == LIMIT)
