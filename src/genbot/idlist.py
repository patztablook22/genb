from typing import Optional, Any

class IdList:
    def __init__(self, data: Optional[list | dict] = None):
        if data is None:
            whitelist = None
            blacklist = None
        if isinstance(data, dict):
            whitelist = data.get('whitelist', None)
            blacklist = data.get('blacklist', None)
        elif isinstance(data, list) or isinstance(data, set):
            whitelist = data
            blacklist = None
        else:
            raise ValueError("Expected either the whitelist (of type list/set) or a dict with the whitelist and blacklist.")

        if whitelist is None:
            self.whitelist = None
        else:
            self.whitelist = set()
            for whitelist_any in whitelist:
                whitelist_int = int(whitelist_any)
                self.whitelist.add(whitelist_int)

        if blacklist is None:
            self.blacklist = None
        else:
            self.blacklist = set()
            for blacklist_any in blacklist:
                blacklist_int = int(blacklist_any)
                self.blacklist.add(blacklist_int)

    def __contains__(self, id):
        if self.whitelist is not None and id not in self.whitelist:
            return False
        if self.blacklist is not None and id in self.blacklist:
            return False
        return True

    def any(self, ids):
        for id in ids:
            if id in self: return True
        return False

    def all(self, ids):
        for id in ids:
            if id not in self: return False
        return True

    def none(self, ids):
        for id in ids:
            if id in self: return False
        return True
