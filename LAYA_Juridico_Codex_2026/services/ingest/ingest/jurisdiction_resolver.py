import re
import unicodedata

STOP={"comunidad","autonoma","ciudad","region","de","del","la","las","el","los","y","comunitat"}


def identity_tokens(value):
    plain="".join(c for c in unicodedata.normalize("NFD",value.casefold()) if not unicodedata.combining(c))
    return frozenset(token for token in re.findall(r"\w+",plain) if token not in STOP)


def region_resolver(entities):
    regions={identity_tokens(e["name"]):e["id"] for e in entities if e["level"] in {"autonomous_community","autonomous_city"}}
    # BOE historical issuer name and current INE name refer to the same exact entity.
    baleares=regions.get(identity_tokens('Balears, Illes'))
    if baleares:regions[identity_tokens('Islas Baleares')]=baleares
    def resolve(parsed):
        if parsed.scope=="Estatal":return "ES"
        if parsed.scope not in {"Autonómico","Autonómica"}:return None
        return regions.get(identity_tokens(parsed.issuer))
    return resolve
